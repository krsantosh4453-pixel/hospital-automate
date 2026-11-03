"""Structured clinical notes (D4)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from clinical.models import ClinicalNote
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import put_in_care
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
URL = "/api/clinical/clinical-notes/"


class StructuredNoteTests(TestCase):
    def setUp(self):
        hospital = Hospital.objects.create(name="A", is_active=True)
        patient = Patient.objects.create(name="Asha", age=40, gender="Female", phone="9999999999", hospital=hospital)
        PatientHospital.objects.create(patient=patient, hospital=hospital, uhid="U1", is_active=True)
        user = User.objects.create_user(username="doc", password="testpass123")
        profile = StaffProfile.objects.create(user=user, role=StaffRole.DOCTOR, employee_id="doc", is_active_staff=True)
        StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=StaffRole.DOCTOR, is_active=True)
        put_in_care(user, hospital, patient)
        self.visit = Visit.objects.get(patient=patient)
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.header = {"HTTP_X_HOSPITAL_ID": str(hospital.pk)}

    def test_sections_are_saved_and_returned(self):
        response = self.client.post(URL, {
            "visit": self.visit.pk, "chief_complaint": "Fever 3 days", "examination": "Temp 39.1",
            "assessment": "Viral fever", "plan": "Paracetamol; review in 3 days",
        }, format="json", **self.header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["plan"], "Paracetamol; review in 3 days")
        note = ClinicalNote.objects.get()
        self.assertEqual(note.as_text().splitlines()[0], "Chief complaint: Fever 3 days")

    def test_free_text_note_still_works(self):
        response = self.client.post(URL, {"visit": self.visit.pk, "note": "Patient comfortable."}, format="json", **self.header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_empty_note_is_refused(self):
        response = self.client.post(URL, {"visit": self.visit.pk, "assessment": "  "}, format="json", **self.header)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_keeps_other_sections(self):
        created = self.client.post(URL, {"visit": self.visit.pk, "assessment": "Viral fever"}, format="json", **self.header)

        updated = self.client.patch(f"{URL}{created.data['id']}/", {"plan": "Fluids"}, format="json", **self.header)

        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
        self.assertEqual((updated.data["assessment"], updated.data["plan"]), ("Viral fever", "Fluids"))
