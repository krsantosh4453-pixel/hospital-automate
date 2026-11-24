"""
Prompt 3 (synthetic data only): allergy status, admitting from the app, ward
medication orders and the discharge in the patient's history.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import Allergy
from doctors.models import Doctor
from hospital.models import Bed, Hospital, Room, Ward
from ipd.models import Admission, DischargePlan, DischargeSummary
from clinical.models import Prescription, PrescriptionItem
from config.hospital_time import hospital_today
from nurses.models import MAR, MARAdministration, Nurse, PatientAssignment
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

User = get_user_model()


def as_user(user, hospital):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.pk))
    return client


class Fixture:
    def build(self):
        self.hospital = Hospital.objects.create(name="Synthetic Clinical Hospital", is_active=True)
        self.doctor_user, _ = make_staff("cw_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.nurse_user, _ = make_staff("cw_nurse", self.hospital, role=StaffRole.NURSE)
        self.desk_user, _ = make_staff("cw_desk", self.hospital, role=StaffRole.RECEPTIONIST)
        self.doctor = Doctor.objects.create(user=self.doctor_user, hospital=self.hospital, name="Dr Synthetic Ward",
                                            specialization="General", phone="9000005001")
        self.patient_user = User.objects.create_user(username="cw_patient", password="synthetic-Pass-123")
        self.patient = Patient.objects.create(user=self.patient_user, name="Synthetic Ward Patient", age=52,
                                              gender="Female", phone="9000005002", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="SCH-1")
        ward = Ward.objects.create(hospital=self.hospital, name="Ward Synthetic", ward_type="General")
        room = Room.objects.create(ward=ward, room_number="S-1", room_type="General")
        self.free_bed = Bed.objects.create(room=room, bed_number="1", status="Available")
        self.taken_bed = Bed.objects.create(room=room, bed_number="2", status="Occupied")

    def admit(self, **body):
        return as_user(self.doctor_user, self.hospital).post(
            "/api/ipd/admissions/",
            {"patient": self.patient.pk, "hospital": self.hospital.pk, "reason": "Synthetic observation", **body},
            format="json",
        )


class AllergyStatusTests(Fixture, TestCase):
    def setUp(self):
        self.build()
        # Clinical records are for the patients in the clinician's care.
        put_in_care(self.doctor_user, self.hospital, self.patient)
        self.doctor_client = as_user(self.doctor_user, self.hospital)

    def status_of(self):
        return self.doctor_client.get(f"/api/patients/{self.patient.pk}/").json()["allergy_status"]

    def set_status(self, value, user=None):
        client = as_user(user, self.hospital) if user else self.doctor_client
        return client.post(f"/api/patients/{self.patient.pk}/allergy-status/", {"status": value}, format="json")

    def test_unknown_is_the_default_and_never_no_known_allergies(self):
        self.assertEqual(self.status_of(), "Unknown")

    def test_no_known_allergies_is_recorded_when_asked(self):
        self.assertEqual(self.set_status("No known allergies").status_code, 200)
        self.assertEqual(self.status_of(), "No known allergies")

    def test_an_allergy_on_record_wins_and_blocks_no_known_allergies(self):
        self.set_status("No known allergies")
        created = self.doctor_client.post("/api/clinical/allergies/", {
            "patient": self.patient.pk, "name": "Penicillin", "reaction": "Hives", "severity": "Moderate",
            "category": "Drug",
        }, format="json")

        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(Allergy.objects.get().category, "Drug")
        self.assertEqual(self.status_of(), "Has allergies")
        refused = self.set_status("No known allergies")
        self.assertEqual(refused.status_code, 409)
        self.assertTrue(refused.json().get("allergy_on_record"))

    def test_removing_the_only_allergy_falls_back_to_unknown_not_none(self):
        self.set_status("No known allergies")
        allergy_id = self.doctor_client.post("/api/clinical/allergies/", {
            "patient": self.patient.pk, "name": "Sulfa", "category": "Drug"}, format="json").json()["id"]

        removed = self.doctor_client.delete(f"/api/clinical/allergies/{allergy_id}/",
                                            {"reason": "Synthetic: recorded on the wrong patient"}, format="json")

        self.assertEqual(removed.status_code, 204, removed.content)
        self.assertEqual(self.status_of(), "Unknown")

    def test_the_front_desk_cannot_change_allergy_status(self):
        self.assertEqual(self.set_status("No known allergies", user=self.desk_user).status_code, 403)
        self.assertEqual(Patient.objects.get(pk=self.patient.pk).allergy_status, "Unknown")

    def test_an_unknown_value_is_refused(self):
        self.assertEqual(self.set_status("Has allergies").status_code, 400)

    # BUG-001 (E2E audit 2026-11-24): the facts the consultation strip relies on.

    def test_staff_outside_doctor_and_nurse_cannot_change_allergy_facts(self):
        for role in (StaffRole.PHARMACIST, StaffRole.LAB_STAFF, StaffRole.RECEPTIONIST):
            user, _ = make_staff(f"cw_{role.lower().replace(' ', '_')}", self.hospital, role=role)
            client = as_user(user, self.hospital)
            with self.subTest(role=role):
                self.assertEqual(self.set_status("No known allergies", user=user).status_code, 403)
                created = client.post("/api/clinical/allergies/", {
                    "patient": self.patient.pk, "name": "Synthetic latex"}, format="json")
                self.assertEqual(created.status_code, 403)
        self.assertEqual(Patient.objects.get(pk=self.patient.pk).allergy_status, "Unknown")
        self.assertFalse(Allergy.objects.exists())

    def test_the_patient_cannot_change_their_own_allergy_facts(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.patient_user)
        self.assertEqual(client.post(f"/api/patients/{self.patient.pk}/allergy-status/",
                                     {"status": "No known allergies"}, format="json").status_code, 403)
        self.assertEqual(client.post("/api/clinical/allergies/", {
            "patient": self.patient.pk, "name": "Synthetic"}, format="json").status_code, 403)
        self.assertEqual(Patient.objects.get(pk=self.patient.pk).allergy_status, "Unknown")

    def test_an_allergy_recorded_at_another_hospital_is_reported_not_hidden(self):
        # The allergy list is scoped to the selected hospital; the status is
        # not, so the strip can ask for a review instead of saying "none".
        other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        Allergy.objects.create(patient=self.patient, hospital=other, name="Synthetic aspirin", category="Drug")
        listed = self.doctor_client.get(f"/api/clinical/allergies/?patient={self.patient.pk}").json()
        rows = listed["results"] if isinstance(listed, dict) else listed
        self.assertEqual(rows, [])
        self.assertEqual(self.status_of(), "Has allergies")
        self.assertEqual(self.set_status("No known allergies").status_code, 409)

    def test_recorded_allergies_survive_a_no_known_allergies_attempt(self):
        self.doctor_client.post("/api/clinical/allergies/", {
            "patient": self.patient.pk, "name": "Synthetic penicillin", "severity": "Severe",
            "category": "Drug"}, format="json")
        self.assertEqual(self.set_status("No known allergies").status_code, 409)
        self.assertEqual(list(Allergy.objects.values_list("name", "severity")), [("Synthetic penicillin", "Severe")])
        self.assertEqual(self.status_of(), "Has allergies")


class AdmissionTests(Fixture, TestCase):
    def setUp(self):
        self.build()

    def test_a_doctor_admits_as_themselves_and_the_stay_starts_admitted(self):
        response = self.admit(status="Discharged", admitting_doctor=999)

        self.assertEqual(response.status_code, 201, response.content)
        admission = Admission.objects.get()
        self.assertEqual((admission.status, admission.admitting_doctor_id), ("Admitted", self.doctor.pk))

    def test_one_active_stay_per_patient(self):
        self.admit()
        again = self.admit()
        self.assertEqual(again.status_code, 409, again.content)
        self.assertEqual(Admission.objects.count(), 1)

    def test_nurses_and_the_desk_cannot_admit(self):
        for user in (self.nurse_user, self.desk_user):
            response = as_user(user, self.hospital).post(
                "/api/ipd/admissions/",
                {"patient": self.patient.pk, "hospital": self.hospital.pk, "reason": "Synthetic"}, format="json")
            self.assertEqual(response.status_code, 403, user.username)
        self.assertFalse(Admission.objects.exists())

    def test_a_patch_cannot_skip_the_discharge_checks(self):
        admission_id = self.admit().json()["id"]
        client = as_user(self.doctor_user, self.hospital)

        client.patch(f"/api/ipd/admissions/{admission_id}/", {"status": "Discharged"}, format="json")

        self.assertEqual(Admission.objects.get(pk=admission_id).status, "Admitted")

    def test_an_occupied_bed_cannot_be_given(self):
        admission_id = self.admit().json()["id"]
        client = as_user(self.doctor_user, self.hospital)
        url = f"/api/ipd/admissions/{admission_id}/allocate_bed/"

        taken = client.post(url, {"bed_id": self.taken_bed.pk}, format="json")
        free = client.post(url, {"bed_id": self.free_bed.pk}, format="json")

        self.assertGreaterEqual(taken.status_code, 400)
        self.assertEqual(free.status_code, 201, free.content)
        self.assertEqual(Bed.objects.get(pk=self.free_bed.pk).status, "Occupied")


class WardMedicationOrderTests(Fixture, TestCase):
    def setUp(self):
        self.build()
        self.admission = Admission.objects.get(pk=self.admit().json()["id"])
        # A ward order comes from the patient's own prescription (as on the web).
        self.prescription = Prescription.objects.create(patient=self.patient, hospital=self.hospital,
                                                        doctor=self.doctor, status="Confirmed")
        self.item = PrescriptionItem.objects.create(prescription=self.prescription,
                                                    name="Synthetic Pantoprazole 40 mg", dosage="40 mg",
                                                    frequency="OD", duration="5 days", quantity=5)
        nurse = Nurse.objects.create(hospital=self.hospital, user=self.nurse_user, name="Nurse Synthetic",
                                     phone="9000005004")
        PatientAssignment.objects.create(nurse=nurse, patient=self.patient, hospital=self.hospital,
                                         shift="Morning", shift_date=hospital_today())

    def order(self, user):
        return as_user(user, self.hospital).post("/api/nurses/mar/", {
            "patient": self.patient.pk, "admission": self.admission.pk, "hospital": self.hospital.pk,
            "prescription": self.prescription.pk, "prescription_item": self.item.pk,
            "medicine_name": "Synthetic Pantoprazole 40 mg", "dose": "40 mg", "route": "IV", "frequency": "OD",
            "start_date": str(date.today()), "instructions": "Before breakfast",
        }, format="json")

    def test_a_doctor_orders_and_nothing_is_marked_given(self):
        response = self.order(self.doctor_user)

        self.assertEqual(response.status_code, 201, response.content)
        mar = MAR.objects.get()
        self.assertEqual((mar.instructions, mar.ordered_by_id), ("Before breakfast", self.doctor_user.pk))
        self.assertFalse(MARAdministration.objects.filter(mar=mar, status="Given").exists())

    def test_a_nurse_reads_orders_but_does_not_write_them(self):
        self.order(self.doctor_user)
        nurse = as_user(self.nurse_user, self.hospital)
        self.assertEqual(self.order(self.nurse_user).status_code, 403)
        rows = nurse.get(f"/api/nurses/mar/?admission={self.admission.pk}").json()
        rows = rows.get("results", rows)
        self.assertEqual([r["medicine_name"] for r in rows], ["Synthetic Pantoprazole 40 mg"])


class DischargeHistoryTests(Fixture, TestCase):
    def setUp(self):
        self.build()
        self.admission = Admission.objects.get(pk=self.admit().json()["id"])
        DischargePlan.objects.create(admission=self.admission, instructions="Review in cardiology OPD in 7 days")
        self.summary = DischargeSummary.objects.create(admission=self.admission,
                                                       summary="Final diagnosis: synthetic angina. Condition: stable.")
        Admission.objects.filter(pk=self.admission.pk).update(status="Discharged",
                                                              discharge_date="2026-11-19T10:00:00Z")

    def discharge_event(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.patient_user)
        events = client.get(f"/api/patients/{self.patient.pk}/timeline/").json()
        events = events.get("events", events) if isinstance(events, dict) else events
        return next(e for e in events if e["kind"] == "Discharge")

    def test_a_draft_summary_is_not_shown_to_the_patient(self):
        detail = self.discharge_event()["detail"]
        self.assertNotIn("Final diagnosis", detail)
        self.assertIn("Review in cardiology OPD", detail)

    def test_the_finalized_summary_and_follow_up_reach_the_patient(self):
        DischargeSummary.objects.filter(pk=self.summary.pk).update(finalized=True)
        detail = self.discharge_event()["detail"]
        self.assertIn("Final diagnosis: synthetic angina", detail)
        self.assertIn("Follow-up: Review in cardiology OPD in 7 days", detail)

    def test_a_patient_cannot_read_someone_elses_history(self):
        other = Patient.objects.create(name="Synthetic Other", age=40, gender="Male", phone="9000005003",
                                       hospital=self.hospital)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.patient_user)
        self.assertEqual(client.get(f"/api/patients/{other.pk}/timeline/").status_code, 404)
