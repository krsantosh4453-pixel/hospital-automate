"""Patient registration, email OTP, and email/password login."""

import re
from datetime import timedelta
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from notifications.models import OTPVerification
from patients.models import Patient
from users.patient_auth import hash_email_otp

User = get_user_model()


def registration_payload(**overrides):
    payload = {
        "role": "Patient",
        "full_name": "Asha Verma",
        "phone": "9811111111",
        "email": "asha@example.com",
        "password": "correct-horse",
        "confirm_password": "correct-horse",
        "date_of_birth": "1990-04-02",
        "gender": "Female",
        "address": "12 Market Road",
    }
    payload.update(overrides)
    return payload


class PatientRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _otp_from_mailbox(self):
        self.assertGreaterEqual(len(mail.outbox), 1)
        match = re.search(r"\b(\d{6})\b", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_registration_hashes_password_and_sends_email_otp(self):
        response = self.client.post("/api/auth/register/", registration_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn("access", response.data)
        self.assertNotIn("otp", response.data)
        user = User.objects.get(email="asha@example.com")
        self.assertNotEqual(user.password, "correct-horse")
        self.assertTrue(user.check_password("correct-horse"))
        patient = Patient.objects.get(user=user)
        self.assertFalse(patient.email_verified)
        self.assertEqual(patient.phone, "9811111111")
        self.assertEqual(patient.address, "12 Market Road")
        self.assertTrue(response.data["verification"]["sent"])
        self.assertEqual(mail.outbox[-1].to, ["asha@example.com"])

    def test_duplicate_email_and_mobile_are_rejected(self):
        self.client.post("/api/auth/register/", registration_payload(), format="json")
        duplicate_email = self.client.post(
            "/api/auth/register/",
            registration_payload(phone="9822222222", email="asha@example.com"),
            format="json",
        )
        self.assertEqual(duplicate_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(duplicate_email.data["error"], "Account already exists with this email.")

        duplicate_phone = self.client.post(
            "/api/auth/register/",
            registration_payload(phone="9811111111", email="other@example.com"),
            format="json",
        )
        self.assertEqual(duplicate_phone.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(duplicate_phone.data["error"], "Account already exists with this mobile number.")
        self.assertEqual(Patient.objects.filter(phone="9811111111").count(), 1)

    def test_invalid_password_is_rejected(self):
        short = self.client.post(
            "/api/auth/register/",
            registration_payload(password="short", confirm_password="short"),
            format="json",
        )
        mismatch = self.client.post(
            "/api/auth/register/",
            registration_payload(password="correct-horse", confirm_password="other-horse"),
            format="json",
        )
        self.assertEqual(short.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="asha@example.com").exists())

    def test_email_otp_expiry_wrong_code_reuse_and_login(self):
        self.client.post("/api/auth/register/", registration_payload(), format="json")
        code = self._otp_from_mailbox()

        wrong = self.client.post(
            "/api/auth/patient/email-otp/verify/",
            {"email": "asha@example.com", "otp": "000000"},
            format="json",
        )
        self.assertEqual(wrong.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong.data["error"], "Invalid OTP.")

        expired = OTPVerification.objects.filter(email="asha@example.com").order_by("-created_at").first()
        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=["expires_at"])
        expired_response = self.client.post(
            "/api/auth/patient/email-otp/verify/",
            {"email": "asha@example.com", "otp": code},
            format="json",
        )
        self.assertEqual(expired_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(expired_response.data["error"], "OTP has expired.")

        OTPVerification.objects.filter(email="asha@example.com").update(
            created_at=timezone.now() - timedelta(minutes=2)
        )
        resent = self.client.post(
            "/api/auth/patient/email-otp/request/",
            {"email": "asha@example.com"},
            format="json",
        )
        self.assertEqual(resent.status_code, status.HTTP_200_OK, resent.data)
        fresh = self._otp_from_mailbox()

        unverified_login = self.client.post(
            "/api/auth/patient/login/",
            {"email": "asha@example.com", "password": "correct-horse"},
            format="json",
        )
        self.assertEqual(unverified_login.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(unverified_login.data["error"], "Email is not verified.")

        verified = self.client.post(
            "/api/auth/patient/email-otp/verify/",
            {"email": "asha@example.com", "otp": fresh},
            format="json",
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK, verified.data)
        self.assertNotIn("access", verified.data)
        self.assertTrue(Patient.objects.get(user__email="asha@example.com").email_verified)

        reused = self.client.post(
            "/api/auth/patient/email-otp/verify/",
            {"email": "asha@example.com", "otp": fresh},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

        wrong_password = self.client.post(
            "/api/auth/patient/login/",
            {"email": "asha@example.com", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(wrong_password.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong_password.data["error"], "Invalid email or password.")

        logged_in = self.client.post(
            "/api/auth/patient/login/",
            {"email": "asha@example.com", "password": "correct-horse"},
            format="json",
        )
        self.assertEqual(logged_in.status_code, status.HTTP_200_OK, logged_in.data)
        self.assertTrue(logged_in.data["access"])
        self.assertTrue(logged_in.data["refresh"])
        self.assertEqual(logged_in.data["patient"]["id"], Patient.objects.get(phone="9811111111").id)

        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-jwt")
        rejected = self.client.get("/api/auth/patient/me/")
        self.assertEqual(rejected.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {logged_in.data['access']}")
        me = self.client.get("/api/auth/patient/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)

        other = User.objects.create_user(username="other_patient", email="other_patient@example.com", password="otherpass123")
        other_patient = Patient.objects.create(
            user=other,
            name="Other Patient",
            age=22,
            gender="Male",
            phone="9833333333",
            email_verified=True,
        )
        hidden = self.client.get(f"/api/patients/{other_patient.id}/")
        self.assertIn(hidden.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        logout = self.client.post(
            "/api/auth/staff/logout/",
            {"refresh": logged_in.data["refresh"]},
            format="json",
        )
        self.assertEqual(logout.status_code, status.HTTP_200_OK)
        self.client.credentials()
        refresh = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": logged_in.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_mobile_otp_is_rejected(self):
        self.client.post("/api/auth/register/", registration_payload(), format="json")
        requested = self.client.post(
            "/api/auth/patient/otp/request/",
            {"phone": "9811111111"},
            format="json",
        )
        self.assertEqual(requested.status_code, status.HTTP_200_OK, requested.data)
        self.assertNotIn("otp", requested.data)
        verified = self.client.post(
            "/api/auth/patient/otp/verify/",
            {"phone": "9811111111", "otp": "111111"},
            format="json",
        )
        self.assertEqual(verified.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(verified.data["error"], "Invalid OTP.")

    @override_settings(
        PATIENT_OTP_DELIVERY="sms",
        TWILIO_ACCOUNT_SID="",
        TWILIO_AUTH_TOKEN="",
        TWILIO_PHONE_NUMBER="",
    )
    def test_mobile_otp_reports_missing_sms_provider(self):
        self.client.post("/api/auth/register/", registration_payload(), format="json")
        response = self.client.post(
            "/api/auth/patient/otp/request/",
            {"phone": "9811111111"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "Unable to send SMS OTP. SMS service is not configured.")
        self.assertFalse(
            OTPVerification.objects.filter(phone="9811111111", channel="sms").exists()
        )

    def test_email_send_failure_does_not_verify_the_account(self):
        with patch("users.patient_auth.send_mail", side_effect=OSError("smtp down")):
            response = self.client.post("/api/auth/register/", registration_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertFalse(response.data["verification"]["sent"])
        self.assertEqual(
            response.data["verification"]["message"],
            "Unable to send verification email. Please check email configuration.",
        )
        self.assertFalse(Patient.objects.get(phone="9811111111").email_verified)

    def test_unsigned_google_token_is_rejected(self):
        with patch("users.patient_auth.urllib.request.urlopen", side_effect=URLError("invalid")):
            response = self.client.post(
                "/api/auth/google/",
                {"credential": "header.payload.signature"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_manual_email_otp_hash_is_not_plaintext(self):
        OTPVerification.objects.create(
            phone="9811111111",
            email="asha@example.com",
            channel="email",
            purpose="verify_email",
            otp="",
            otp_hash=hash_email_otp("asha@example.com", "123456"),
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        stored = OTPVerification.objects.get(email="asha@example.com")
        self.assertNotIn("123456", stored.otp_hash)
        self.assertEqual(stored.otp, "")
