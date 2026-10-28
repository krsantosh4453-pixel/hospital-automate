"""Patient timeline / longitudinal record (B9, D12)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import ClinicalNote, Diagnosis
from encounters.models import Visit
from hospital.models import Hospital
from laboratory.models import LabTest
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import put_in_care
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()


def staff(username, hospital, role):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=username, is_active_staff=True)
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user


class TimelineTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="A", is_active=True)
        self.other = Hospital.objects.create(name="B", is_active=True)
        self.patient = Patient.objects.create(name="Asha", age=40, gender="Female", phone="9999999999", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="A1", is_active=True)
        PatientHospital.objects.create(patient=self.patient, hospital=self.other, uhid="B1", is_active=True)
        self.doctor_user = staff("doc", self.hospital, StaffRole.DOCTOR)
        put_in_care(self.doctor_user, self.hospital, self.patient)
        visit = Visit.objects.filter(patient=self.patient, hospital=self.hospital).first()
        Diagnosis.objects.create(visit=visit, name="Hypertension", icd10_code="I10")
        ClinicalNote.objects.create(visit=visit, note="Private doctor note")
        LabTest.objects.create(hospital=self.hospital, patient=self.patient, name="CBC", status="Released", result="Normal")
        LabTest.objects.create(hospital=self.hospital, patient=self.patient, name="Lipids", status="Processing")
        LabTest.objects.create(hospital=self.other, patient=self.patient, name="HbA1c at B", status="Released", result="6.1")
        self.client = APIClient()

    def url(self):
        return f"/api/patients/{self.patient.pk}/timeline/"

    def kinds_and_titles(self, response):
        return {(e["kind"], e["title"]) for e in response.data["events"]}

    def test_doctor_sees_this_hospitals_history_newest_first(self):
        self.client.force_authenticate(user=self.doctor_user)

        response = self.client.get(self.url(), HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found = self.kinds_and_titles(response)
        self.assertIn(("Diagnosis", "Provisional: Hypertension (I10)"), found)
        self.assertIn(("Lab", "Lipids"), found)
        self.assertIn(("Doctor note", "Doctor note"), found)
        self.assertNotIn(("Lab", "HbA1c at B"), found)  # another hospital's record
        times = [e["when"] for e in response.data["events"]]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_every_read_is_audited(self):
        self.client.force_authenticate(user=self.doctor_user)

        self.client.get(self.url(), HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertTrue(AuditLog.objects.filter(action="patients.timeline.read", user=self.doctor_user).exists())

    def test_patient_view_hides_notes_and_unreleased_results(self):
        login = User.objects.create_user(username="asha", password="testpass123")
        self.patient.user = login
        self.patient.save(update_fields=["user"])
        self.client.force_authenticate(user=login)

        response = self.client.get(self.url())

        found = self.kinds_and_titles(response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(("Lab", "CBC"), found)
        self.assertIn(("Lab", "HbA1c at B"), found)  # the patient's own record at every hospital
        self.assertNotIn(("Lab", "Lipids"), found)
        self.assertFalse(any(kind == "Doctor note" for kind, _ in found))

    def test_receptionist_and_doctor_without_care_are_refused(self):
        receptionist = staff("rec", self.hospital, StaffRole.RECEPTIONIST)
        stranger = staff("doc2", self.hospital, StaffRole.DOCTOR)

        self.client.force_authenticate(user=receptionist)
        refused = self.client.get(self.url(), HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        self.client.force_authenticate(user=stranger)
        hidden = self.client.get(self.url(), HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)
