"""FHIR R4 read API: access control, hospital isolation, safe data and the main reads (synthetic data)."""

from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import Allergy, ClinicalNote, Diagnosis, Prescription, PrescriptionItem, VitalSign
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from laboratory.models import LabResult, LabTest
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

FHIR_JSON = "application/fhir+json"


@override_settings(FHIR_ENABLED=True)
class FHIRApiTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(
            name="Synthetic FHIR Hospital", is_active=True, address="1 Hospital Road", city="Patna", state="Bihar"
        )
        self.other = Hospital.objects.create(name="Other Hospital", is_active=True)
        self.admin, _ = make_staff("fhir_admin", self.hospital, role=StaffRole.ADMIN)
        self.doctor_user, _ = make_staff("fhir_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.other_admin, _ = make_staff("fhir_other_admin", self.other, role=StaffRole.ADMIN)

        self.doctor = Doctor.objects.create(
            hospital=self.hospital, user=self.doctor_user, name="Dr Synthetic", specialization="General",
            phone="9000000040",
        )
        self.patient = Patient.objects.create(
            name="Asha Devi", age=40, gender="Female", phone="9000000041", hospital=self.hospital,
            date_of_birth=date(1985, 6, 15), address_line="12 Gandhi Nagar", city="Gaya", pincode="823001",
        )
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="UH-100")
        self.outsider = Patient.objects.create(
            name="Other Patient", age=30, gender="Male", phone="9000000042", hospital=self.other
        )
        PatientHospital.objects.create(patient=self.outsider, hospital=self.other, uhid="OT-1")

        self.visit = Visit.objects.create(
            patient=self.patient, hospital=self.hospital, doctor=self.doctor, chief_complaint="Fever"
        )
        self.vitals = VitalSign.objects.create(visit=self.visit, temperature=38.4, heart_rate=96)
        Diagnosis.objects.create(visit=self.visit, name="Viral fever", icd10_code="A99")
        Allergy.objects.create(patient=self.patient, hospital=self.hospital, name="Penicillin", severity="Severe")
        ClinicalNote.objects.create(visit=self.visit, doctor=self.doctor, note="Fever for three days")
        prescription = Prescription.objects.create(
            hospital=self.hospital, patient=self.patient, doctor=self.doctor, visit=self.visit
        )
        self.item = PrescriptionItem.objects.create(
            prescription=prescription, name="Paracetamol", dosage="650 mg", frequency="BD", quantity=6
        )
        released = LabTest.objects.create(
            hospital=self.hospital, name="CBC", patient=self.patient, doctor=self.doctor, visit=self.visit,
            status="Released",
        )
        LabResult.objects.create(lab_test=released, result_data={"Hemoglobin": 12.1}, is_released=True)
        self.pending = LabTest.objects.create(
            hospital=self.hospital, name="LFT", patient=self.patient, doctor=self.doctor, visit=self.visit,
            status="Result Entered",
        )
        LabResult.objects.create(lab_test=self.pending, result_data={"Bilirubin": 9.9}, is_released=False)

        self.client = self._client(self.admin)

    def _client(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        if user is not None:
            client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def _entries(self, resp, resource_type=None):
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["resourceType"], "Bundle")
        resources = [e["resource"] for e in body["entry"]]
        if resource_type:
            resources = [r for r in resources if r["resourceType"] == resource_type]
        return resources

    # Access ---------------------------------------------------------------

    @override_settings(FHIR_ENABLED=False)
    def test_disabled_api_returns_not_found(self):
        resp = self.client.get("/api/fhir/Patient")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["resourceType"], "OperationOutcome")

    def test_metadata_is_public_and_lists_resources(self):
        resp = APIClient().get("/api/fhir/metadata")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], FHIR_JSON)
        types = {r["type"] for r in resp.json()["rest"][0]["resource"]}
        self.assertTrue({"Patient", "Observation", "MedicationRequest", "DiagnosticReport"} <= types)

    def test_anonymous_request_is_refused_as_operation_outcome(self):
        resp = self._client(None).get("/api/fhir/Patient")
        self.assertIn(resp.status_code, (401, 403))
        self.assertEqual(resp.json()["resourceType"], "OperationOutcome")
        self.assertEqual(resp["Content-Type"], FHIR_JSON)

    def test_doctor_cannot_bulk_export(self):
        resp = self._client(self.doctor_user).get("/api/fhir/Patient")
        self.assertEqual(resp.status_code, 403)

    def test_admin_of_another_hospital_is_refused(self):
        resp = self._client(self.other_admin).get("/api/fhir/Patient")
        self.assertEqual(resp.status_code, 403)

    def test_single_hospital_admin_needs_no_header(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        self.assertEqual(client.get("/api/fhir/Organization").status_code, 200)

    # Isolation and data safety ---------------------------------------------

    def test_patient_search_only_sees_this_hospital(self):
        names = [r["name"][0]["given"][0] for r in self._entries(self.client.get("/api/fhir/Patient"))]
        self.assertEqual(names, ["Asha"])

    def test_other_hospitals_patient_is_not_found(self):
        resp = self.client.get(f"/api/fhir/Patient/Patient-{self.outsider.pk}")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["issue"][0]["code"], "not-found")

    def test_patient_uses_recorded_birth_date_and_own_address(self):
        resp = self.client.get(f"/api/fhir/Patient/Patient-{self.patient.pk}")
        self.assertEqual(resp.status_code, 200, resp.content)
        patient = resp.json()
        self.assertEqual(patient["birthDate"], "1985-06-15")
        self.assertEqual(patient["address"][0]["city"], "Gaya")
        self.assertNotIn("Patna", str(patient["address"]))

    def test_age_only_patient_gets_year_precision_birth_date(self):
        self.patient.date_of_birth = None
        self.patient.save(update_fields=["date_of_birth"])
        patient = self.client.get(f"/api/fhir/Patient/Patient-{self.patient.pk}").json()
        self.assertEqual(patient["birthDate"], str(date.today().year - 40))

    def test_unreleased_lab_values_are_not_exported(self):
        observations = self._entries(self.client.get(f"/api/fhir/Observation?patient=Patient/Patient-{self.patient.pk}"))
        codes = {o["code"]["text"] for o in observations}
        self.assertIn("Hemoglobin", codes)
        self.assertNotIn("Bilirubin", codes)
        reports = self._entries(self.client.get("/api/fhir/DiagnosticReport"))
        self.assertEqual([r["code"]["text"] for r in reports], ["CBC"])
        self.assertEqual(self.client.get(f"/api/fhir/DiagnosticReport/DiagnosticReport-{self.pending.pk}").status_code, 404)

    # Reads and searches ----------------------------------------------------

    def test_patient_search_by_uhid_and_name(self):
        self.assertEqual(len(self._entries(self.client.get("/api/fhir/Patient?identifier=UH-100"))), 1)
        self.assertEqual(len(self._entries(self.client.get("/api/fhir/Patient?identifier=OT-1"))), 0)
        self.assertEqual(len(self._entries(self.client.get("/api/fhir/Patient?name=asha"))), 1)

    def test_medication_request_read_by_item_id(self):
        resp = self.client.get(f"/api/fhir/MedicationRequest/MedicationRequest-{self.item.pk}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["medicationReference"]["display"], "Paracetamol")

    def test_vital_sign_observation_read(self):
        resp = self.client.get(f"/api/fhir/Observation/Observation-temperature-{self.vitals.pk}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["valueQuantity"]["value"], 38.4)

    def test_everything_bundles_the_patient_record(self):
        resp = self.client.get(f"/api/fhir/Patient/Patient-{self.patient.pk}/$everything")
        types = {r["resourceType"] for r in self._entries(resp)}
        self.assertTrue({"Patient", "Encounter", "Observation", "Condition", "MedicationRequest",
                         "AllergyIntolerance", "DiagnosticReport", "DocumentReference"} <= types)
        self.assertNotIn("OperationOutcome", types)

    def test_paging_links(self):
        Visit.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor)
        body = self.client.get("/api/fhir/Encounter?_count=1").json()
        self.assertEqual(len(body["entry"]), 1)
        relations = {link["relation"]: link["url"] for link in body["link"]}
        self.assertIn("_offset=1", relations["next"])
        last = self.client.get("/api/fhir/Encounter?_count=1&_offset=1").json()
        self.assertEqual(len(last["entry"]), 1)
        self.assertNotIn("next", {link["relation"] for link in last["link"]})

    def test_bad_input_is_rejected(self):
        self.assertEqual(self.client.get("/api/fhir/Observation?patient=abc").status_code, 400)
        self.assertEqual(self.client.get("/api/fhir/Encounter?_count=x").status_code, 400)
        self.assertEqual(self.client.get("/api/fhir/Spaceship").status_code, 404)

    def test_reads_are_audited(self):
        self.client.get(f"/api/fhir/Patient/Patient-{self.patient.pk}")
        self.client.get("/api/fhir/Condition")
        actions = list(AuditLog.objects.filter(user=self.admin).values_list("action", flat=True))
        self.assertIn("fhir.read", actions)
        self.assertIn("fhir.search", actions)
