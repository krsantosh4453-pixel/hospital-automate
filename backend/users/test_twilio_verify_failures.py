"""Twilio Verify failure handling and the local patient SMS OTP attempt cap.

The Twilio client is replaced with a fake here: these tests prove our error
handling, not delivery. Real delivery is checked with `manage.py check_providers`.
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from twilio.base.exceptions import TwilioRestException

from patients.models import Patient
from notifications.models import OTPVerification
from users.patient_auth import OTP_ATTEMPT_LIMIT, request_patient_otp, verify_patient_otp
from users.twilio_verify import TwilioVerifyService, VerifyResult, mask_phone

PHONE = "9876501234"
User = get_user_model()


def rest_error(code, status=400):
    return TwilioRestException(status, "https://verify.twilio.com/v2/Services/VA1/Verifications",
                               msg=f"failure for +91{PHONE}", code=code)


def service_with(create_side_effect=None, check_side_effect=None):
    """A configured TwilioVerifyService whose client calls are faked."""
    service = TwilioVerifyService()
    service._initialized = True
    service._verify_service_sid = "VA" + "0" * 32
    endpoint = mock.MagicMock()
    endpoint.verifications.create.side_effect = create_side_effect
    endpoint.verification_checks.create.side_effect = check_side_effect
    service._client = mock.MagicMock()
    service._client.verify.v2.services.return_value = endpoint
    return service, endpoint


class TwilioVerifyErrorMappingTests(TestCase):
    def assert_no_phone_in_logs(self, logs):
        self.assertNotIn(PHONE, "\n".join(logs.output))

    def test_bad_credentials_are_reported_as_configuration_errors(self):
        service, _ = service_with(create_side_effect=rest_error(20003, status=401))
        with self.assertLogs("users.twilio_verify", level="WARNING") as logs:
            result = service.start_verification(PHONE)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "provider_auth")
        self.assertIn("CRITICAL", logs.output[0])
        self.assert_no_phone_in_logs(logs)

    def test_send_rate_limit_says_too_many(self):
        service, _ = service_with(create_side_effect=rest_error(60203, status=429))
        with self.assertLogs("users.twilio_verify", level="WARNING") as logs:
            result = service.start_verification(PHONE)
        self.assertEqual(result.reason, "limited")
        self.assertIn("Too many", result.message)
        self.assert_no_phone_in_logs(logs)

    def test_invalid_number_is_reported(self):
        service, _ = service_with(create_side_effect=rest_error(60200))
        with self.assertLogs("users.twilio_verify", level="WARNING"):
            result = service.start_verification(PHONE)
        self.assertEqual(result.reason, "invalid_number")

    def test_trial_unverified_number_is_undeliverable(self):
        service, _ = service_with(create_side_effect=rest_error(21608))
        with self.assertLogs("users.twilio_verify", level="WARNING"):
            result = service.start_verification(PHONE)
        self.assertEqual(result.reason, "undeliverable")

    def test_network_failure_is_a_provider_error(self):
        service, _ = service_with(create_side_effect=ConnectionError(f"+91{PHONE} unreachable"))
        with self.assertLogs("users.twilio_verify", level="ERROR") as logs:
            result = service.start_verification(PHONE)
        self.assertEqual(result.reason, "provider_error")
        self.assert_no_phone_in_logs(logs)

    def test_expired_verification_on_check_is_invalid_or_expired(self):
        service, _ = service_with(check_side_effect=rest_error(20404, status=404))
        with self.assertLogs("users.twilio_verify", level="WARNING"):
            result = service.check_verification(PHONE, "123456")
        self.assertEqual(result.reason, "expired")
        self.assertEqual(result.message, "Invalid or expired OTP.")

    def test_too_many_checks_says_too_many(self):
        service, _ = service_with(check_side_effect=rest_error(60202, status=429))
        with self.assertLogs("users.twilio_verify", level="WARNING"):
            result = service.check_verification(PHONE, "123456")
        self.assertEqual(result.reason, "limited")
        self.assertIn("Too many", result.message)

    def test_wrong_code_is_rejected_and_right_code_approved(self):
        service, endpoint = service_with()
        endpoint.verification_checks.create.return_value = SimpleNamespace(status="pending", sid="VE1")
        self.assertEqual(service.check_verification(PHONE, "111111").reason, "rejected")
        endpoint.verification_checks.create.return_value = SimpleNamespace(status="approved", sid="VE1")
        self.assertTrue(service.check_verification(PHONE, "222222").ok)

    def test_successful_send_logs_a_masked_number_only(self):
        service, endpoint = service_with()
        endpoint.verifications.create.return_value = SimpleNamespace(status="pending", sid="VE1")
        with self.assertLogs("users.twilio_verify", level="INFO") as logs:
            result = service.start_verification(PHONE)
        self.assertTrue(result.ok)
        self.assert_no_phone_in_logs(logs)
        self.assertIn(mask_phone(PHONE), "\n".join(logs.output))
        endpoint.verifications.create.assert_called_once_with(to=f"+91{PHONE}", channel="sms")

    def test_unconfigured_service_never_calls_twilio(self):
        service = TwilioVerifyService()
        service._initialized = True
        with self.assertLogs("users.twilio_verify", level="ERROR"):
            result = service.start_verification(PHONE)
        self.assertEqual(result.reason, "not_configured")


@override_settings(PATIENT_OTP_DELIVERY="sms")
class PatientSmsOtpAttemptCapTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="sms_cap_patient", password="x-pass-12345")
        Patient.objects.create(user=user, name="Cap Patient", age=30, gender="Female", phone=PHONE)
        self.verify = mock.MagicMock()
        self.verify.is_configured.return_value = True
        self.verify.start_verification.return_value = VerifyResult(True, "sent", "VE1", reason="sent")
        self.verify.check_verification.return_value = VerifyResult(False, "Invalid or expired OTP.", reason="rejected")
        patcher = mock.patch("users.sms.get_twilio_verify_service", return_value=self.verify)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_attempts_are_capped_locally_before_reaching_twilio(self):
        status_name, _, delivery = request_patient_otp(PHONE)
        self.assertEqual((status_name, delivery), ("pending", "sms"))
        for _ in range(OTP_ATTEMPT_LIMIT):
            patient, error = verify_patient_otp(PHONE, "000000")
            self.assertIsNone(patient)
            self.assertEqual(error, "Invalid or expired OTP.")
        patient, error = verify_patient_otp(PHONE, "000000")
        self.assertIsNone(patient)
        self.assertIn("Too many", error)
        self.assertEqual(self.verify.check_verification.call_count, OTP_ATTEMPT_LIMIT)

    def test_expired_otp_is_refused_without_calling_twilio(self):
        request_patient_otp(PHONE)
        OTPVerification.objects.filter(phone=PHONE).update(expires_at=timezone.now() - timedelta(seconds=1))
        patient, error = verify_patient_otp(PHONE, "123456")
        self.assertIsNone(patient)
        self.assertEqual(error, "Invalid or expired OTP.")
        self.verify.check_verification.assert_not_called()

    def test_verify_without_a_request_is_refused(self):
        patient, error = verify_patient_otp(PHONE, "123456")
        self.assertIsNone(patient)
        self.verify.check_verification.assert_not_called()

    def test_approved_code_signs_in_and_marks_phone_verified(self):
        request_patient_otp(PHONE)
        self.verify.check_verification.return_value = VerifyResult(True, "ok", "VE1", reason="approved")
        patient, error = verify_patient_otp(PHONE, "123456")
        self.assertIsNone(error)
        self.assertTrue(patient.phone_verified)
        self.assertTrue(OTPVerification.objects.get(phone=PHONE).is_verified)
