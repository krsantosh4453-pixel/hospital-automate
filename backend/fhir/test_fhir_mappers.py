"""
FHIR R4 mappers served by /api/fhir/ (fhir/sources.py), on synthetic data:
the branches the API tests do not reach (Practitioner, lab values with
ranges and flags, dosage parsing, encounter diagnoses and IPD stays).
"""

from django.test import TestCase

from clinical.models import Diagnosis, Prescription, PrescriptionItem
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from interoperability.fhir.mappings.base import MappingContext
from interoperability.fhir.mappings.encounter import VisitEncounterMapper
from interoperability.fhir.mappings.medication import PrescriptionMedicationRequestMapper
from interoperability.fhir.mappings.observation import LabResultObservationMapper
from interoperability.fhir.mappings.practitioner import PractitionerMapper
from laboratory.models import LabResult, LabTest
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class FHIRMapperTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic FHIR Map", is_active=True)
        cls.context = MappingContext(hospital_id=cls.hospital.id)
        doctor_user, _ = make_staff("fhir_map_doc", cls.hospital, role=StaffRole.DOCTOR)
        cls.lab_user, _ = make_staff("fhir_map_lab", cls.hospital, role=StaffRole.LAB_STAFF)
        # Doctor ids must not line up with login ids, or a wrong reference would pass.
        Doctor.objects.create(hospital=cls.hospital, name="Placeholder", specialization="", phone="")
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, user=doctor_user, name="Asha Verma",
                                           specialization="Cardiology", phone="9000000601")
        cls.patient = Patient.objects.create(name="Synthetic Map Patient", age=50, gender="Male",
                                             phone="9000000602", hospital=cls.hospital)
        cls.visit = Visit.objects.create(patient=cls.patient, hospital=cls.hospital, doctor=cls.doctor,
                                         chief_complaint="Chest pain")

    # Practitioner

    def test_practitioner_has_name_specialty_and_availability(self):
        resource = PractitionerMapper(self.context).map(self.doctor)
        self.assertEqual(resource["resourceType"], "Practitioner")
        self.assertEqual(resource["id"], f"Practitioner-{self.doctor.id}")
        self.assertTrue(resource["active"])
        self.assertEqual(resource["name"][0]["family"], "Verma")
        self.assertEqual(resource["name"][0]["given"], ["Asha"])
        self.assertEqual(resource["qualification"][0]["code"]["text"], "Cardiology")
        self.assertEqual(resource["telecom"][0]["value"], "9000000601")

    def test_practitioner_on_leave_is_inactive(self):
        on_leave = Doctor.objects.create(hospital=self.hospital, name="Ravi", status="On Leave",
                                         specialization="", phone="")
        resource = PractitionerMapper(self.context).map(on_leave)
        self.assertFalse(resource["active"])
        self.assertEqual(resource["name"][0]["family"], "Ravi")
        self.assertEqual(resource["telecom"], [])
        self.assertNotIn("qualification", resource)

    # Lab result observations

    def lab_result(self, entered_by=None, **values):
        test = LabTest.objects.create(hospital=self.hospital, name="Panel", patient=self.patient,
                                      doctor=self.doctor, visit=self.visit, status="Released")
        return LabResult.objects.create(lab_test=test, is_released=True, entered_by=entered_by, **values)

    def test_numeric_value_gets_unit_range_and_flag(self):
        result = self.lab_result(
            result_data={"Hemoglobin": 9.1, "Remark": "Sample slightly haemolysed"},
            reference_ranges={"Hemoglobin": {"low": 12, "high": 16, "unit": "g/dL"}},
            abnormal_flags={"Hemoglobin": "L"}, is_verified=True, result_text="Repeat in a week",
        )
        by_code = {o["code"]["text"]: o for o in LabResultObservationMapper(self.context).map(result)}

        hb = by_code["Hemoglobin"]
        self.assertEqual(hb["status"], "final")
        self.assertEqual(hb["valueQuantity"]["value"], 9.1)
        self.assertEqual(hb["valueQuantity"]["unit"], "g/dL")
        self.assertEqual(hb["referenceRange"][0]["low"]["value"], 12.0)
        self.assertEqual(hb["referenceRange"][0]["high"]["value"], 16.0)
        self.assertEqual(hb["interpretation"][0]["coding"][0]["code"], "L")
        self.assertEqual(hb["subject"]["reference"], f"Patient/Patient-{self.patient.id}")
        self.assertEqual(hb["note"], [{"text": "Repeat in a week"}])

        remark = by_code["Remark"]
        self.assertEqual(remark["valueString"], "Sample slightly haemolysed")
        self.assertNotIn("referenceRange", remark)
        self.assertNotIn("interpretation", remark)

    def test_unverified_result_is_preliminary_and_list_flags_mean_abnormal(self):
        result = self.lab_result(result_data={"Glucose": 250, "Ketones": True}, abnormal_flags=["Glucose"])
        by_code = {o["code"]["text"]: o for o in LabResultObservationMapper(self.context).map(result)}
        self.assertEqual(by_code["Glucose"]["status"], "preliminary")
        self.assertEqual(by_code["Glucose"]["interpretation"][0]["coding"][0]["code"], "A")
        self.assertIs(by_code["Ketones"]["valueBoolean"], True)
        self.assertNotIn("valueQuantity", by_code["Ketones"])

    def test_performer_points_to_the_doctor_resource_not_a_login_id(self):
        result = self.lab_result(result_data={"Sodium": 138}, entered_by=self.doctor.user)
        [obs] = LabResultObservationMapper(self.context).map(result)
        self.assertEqual(obs["performer"][0]["actor"]["reference"], f"Practitioner/Practitioner-{self.doctor.id}")

    def test_lab_staff_performer_is_named_without_a_dangling_reference(self):
        # Lab Staff have no Practitioner resource here, so only their name is given.
        result = self.lab_result(result_data={"Sodium": 138}, entered_by=self.lab_user)
        [obs] = LabResultObservationMapper(self.context).map(result)
        actor = obs["performer"][0]["actor"]
        self.assertNotIn("reference", actor)
        self.assertTrue(actor["display"])

    # Medication requests

    def test_dosage_duration_and_quantity_are_parsed(self):
        prescription = Prescription.objects.create(hospital=self.hospital, patient=self.patient,
                                                   doctor=self.doctor, visit=self.visit)
        PrescriptionItem.objects.create(prescription=prescription, name="Amoxicillin", dosage="500 mg",
                                        frequency="TDS", duration="5 days", quantity=15,
                                        instructions="After food")
        PrescriptionItem.objects.create(prescription=prescription, name="ORS", dosage="as needed", quantity=0)
        by_name = {r["medicationCodeableConcept"]["text"]: r
                   for r in PrescriptionMedicationRequestMapper(self.context).map(prescription)}

        amox = by_name["Amoxicillin"]
        dosage = amox["dosageInstruction"][0]
        self.assertEqual(dosage["doseAndRate"][0]["doseQuantity"]["value"], 500.0)
        self.assertEqual(dosage["doseAndRate"][0]["doseQuantity"]["unit"], "mg")
        self.assertEqual(dosage["timing"]["code"]["text"], "TDS")
        self.assertIn("Duration: 5 days", dosage["text"])
        self.assertEqual(amox["dispenseRequest"]["quantity"]["value"], 15.0)
        self.assertEqual(amox["dispenseRequest"]["expectedSupplyDuration"]["value"], 5.0)
        self.assertEqual(amox["note"], [{"text": "After food"}])

        ors = by_name["ORS"]
        self.assertNotIn("dispenseRequest", ors)

    # Encounters

    def test_encounter_lists_its_diagnoses_and_reason(self):
        Diagnosis.objects.create(visit=self.visit, name="Angina", icd10_code="I20.9")
        resource = VisitEncounterMapper(self.context).map(self.visit)
        self.assertEqual(resource["reasonCode"][0]["text"], "Chest pain")
        self.assertEqual([d["condition"]["display"] for d in resource["diagnosis"]], ["Angina"])
        self.assertNotIn("hospitalization", resource)

    def test_inpatient_encounter_has_hospitalization(self):
        stay = Visit.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor,
                                    visit_type="IPD")
        resource = VisitEncounterMapper(self.context).map(stay)
        self.assertIn("admitSource", resource["hospitalization"])
