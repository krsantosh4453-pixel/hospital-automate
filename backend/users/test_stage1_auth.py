"""Stage 1 authentication, patient isolation, and audit permission tests."""

import json
from datetime import time
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from appointments.models import Appointment
from audit.models import AIInteraction, AuditLog
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient
from users.models import StaffHospitalMembership, StaffProfile, StaffRole
from users.patient_auth import normalize_phone

User = get_user_model()


def staff_membership(user, hospital, role):
    profile = StaffProfile.objects.create(
        user=user,
        role=role,
        employee_id=f"EMP-{user.username}",
        is_active_staff=True,
    )
    StaffHospitalMembership.objects.create(
        staff=profile,
        hospital=hospital,
        role=role,
        is_active=True,
    )
    return profile


@override_settings(PATIENT_OTP_DELIVERY="cache", GOOGLE_CLIENT_ID="test-google-client")
class Stage1AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="City Hospital", is_active=True)
        self.other_hospital = Hospital.objects.create(name="Other Hospital", is_active=True)

        self.admin = User.objects.create_user(username="admin_stage1", password="adminpass123")
        staff_membership(self.admin, self.hospital, StaffRole.ADMIN)

        self.doctor_user = User.objects.create_user(username="doctor_stage1", password="doctorpass123")
        staff_membership(self.doctor_user, self.hospital, StaffRole.DOCTOR)

        self.nurse_user = User.objects.create_user(username="nurse_stage1", password="nursepass123")
        staff_membership(self.nurse_user, self.hospital, StaffRole.NURSE)

        self.compounder_user = User.objects.create_user(
            username="compounder_stage1",
            password="compounderpass123",
        )
        staff_membership(self.compounder_user, self.hospital, StaffRole.COMPOUNDER)

        self.patient_user = User.objects.create_user(
            username="patient_stage1",
            email="patient_stage1@example.com",
            password="patientpass123",
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            name="Patient One",
            age=30,
            gender="Female",
            phone="9876543210",
            hospital=self.hospital,
        )
        self.other_user = User.objects.create_user(
            username="patient_other",
            password="otherpass123",
        )
        self.other_patient = Patient.objects.create(
            user=self.other_user,
            name="Patient Two",
            age=40,
            gender="Male",
            phone="9123456780",
            hospital=self.hospital,
        )
        self.doctor = Doctor.objects.create(
            hospital=self.hospital,
            name="Dr. Stage",
            specialization="Medicine",
            phone="9000000001",
        )
        self.own_appointment = Appointment.objects.create(
            hospital=self.hospital,
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=timezone.now().date(),
            appointment_time=time(10, 0),
        )
        self.other_appointment = Appointment.objects.create(
            hospital=self.hospital,
            patient=self.other_patient,
            doctor=self.doctor,
            appointment_date=timezone.now().date(),
            appointment_time=time(11, 0),
        )

    def _patient_token(self, username="patient_stage1", password="patientpass123"):
        response = self.client.post(
            "/api/auth/patient/token/",
            {"identifier": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["access"]

    def test_invalid_otp_is_rejected(self):
        requested = self.client.post(
            "/api/auth/patient/otp/request/",
            {"phone": "9876543210"},
            format="json",
        )
        self.assertEqual(requested.status_code, status.HTTP_200_OK)
        self.assertNotIn("otp", requested.data)
        verified = self.client.post(
            "/api/auth/patient/otp/verify/",
            {"phone": "9876543210", "otp": "000000"},
            format="json",
        )
        self.assertEqual(verified.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_otp_returns_jwt_and_survives_me(self):
        self.client.post("/api/auth/patient/otp/request/", {"phone": "9876543210"}, format="json")
        otp = cache.get(f"patient-otp:{normalize_phone('9876543210')}")
        self.assertIsNotNone(otp)
        verified = self.client.post(
            "/api/auth/patient/otp/verify/",
            {"phone": "9876543210", "otp": otp},
            format="json",
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.assertIn("access", verified.data)
        self.assertIn("refresh", verified.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {verified.data['access']}")
        me = self.client.get("/api/auth/patient/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["patient"]["id"], self.patient.id)

    def test_invalid_patient_password_is_rejected(self):
        response = self.client.post(
            "/api/auth/patient/token/",
            {"identifier": str(self.patient.id), "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_cannot_read_another_patients_appointments(self):
        token = self._patient_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/appointments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data)
        ids = [row["id"] for row in rows]
        self.assertIn(self.own_appointment.id, ids)
        self.assertNotIn(self.other_appointment.id, ids)

    def test_patient_cannot_access_staff_apis(self):
        token = self._patient_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        for path in ("/api/doctors/", "/api/compounder/", "/api/hospital/hospitals/", "/api/audit/audit-logs/"):
            response = self.client.get(path)
            self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN), path)

    def test_unsigned_google_token_is_rejected(self):
        with patch("users.patient_auth.urllib.request.urlopen", side_effect=URLError("invalid")):
            response = self.client.post(
                "/api/auth/google/",
                {"credential": "header.payload.signature"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_verified_google_token_returns_jwt(self):
        payload = {
            "aud": "test-google-client",
            "iss": "https://accounts.google.com",
            "email_verified": "true",
            "sub": "google-subject-1",
            "email": "google.patient@example.com",
            "name": "Google Patient",
        }

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        with patch("users.patient_auth.urllib.request.urlopen", return_value=FakeResponse()):
            response = self.client.post(
                "/api/auth/google/",
                {"credential": "signed-token"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["account_type"], "patient")

    def test_audit_log_is_admin_read_only(self):
        AuditLog.objects.create(user=self.admin, action="CREATE", model_name="Patient", object_id="1")
        self.client.force_authenticate(user=self.doctor_user)
        self.assertEqual(self.client.get("/api/audit/audit-logs/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post("/api/audit/audit-logs/", {"action": "TAMPER"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(user=self.nurse_user)
        self.assertEqual(self.client.get("/api/audit/audit-logs/").status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.compounder_user)
        self.assertEqual(self.client.get("/api/audit/audit-logs/").status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        listed = self.client.get("/api/audit/audit-logs/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        created = self.client.post("/api/audit/audit-logs/", {"action": "TAMPER"}, format="json")
        self.assertEqual(created.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        existing = AuditLog.objects.first()
        updated = self.client.patch(f"/api/audit/audit-logs/{existing.id}/", {"action": "EDIT"}, format="json")
        deleted = self.client.delete(f"/api/audit/audit-logs/{existing.id}/")
        self.assertEqual(updated.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(deleted.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_ai_interaction_cannot_be_written_by_clients(self):
        AIInteraction.objects.create(input_text="note", ai_output="draft")
        self.client.force_authenticate(user=self.patient_user)
        self.assertEqual(self.client.get("/api/audit/ai-interactions/").status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.doctor_user)
        self.assertEqual(self.client.get("/api/audit/ai-interactions/").status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post("/api/audit/ai-interactions/", {"input_text": "x", "ai_output": "y"}, format="json").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.get("/api/audit/ai-interactions/").status_code, status.HTTP_200_OK)

    def test_staff_login_still_rejects_invalid_password(self):
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_stage1", "password": "nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
