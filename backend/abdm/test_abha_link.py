"""ABHA verify-and-link flow against a mocked ABDM sandbox (synthetic data, no network)."""

import base64
import json
from unittest import mock

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from abdm.models import ABHALink
from audit.models import AuditLog
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

ABHA = "91-1234-5678-9012"
OTHER_ABHA = "91-0000-1111-2222"
SANDBOX = dict(
    ABDM_ENABLED=True,
    ABDM_BASE_URL="https://gateway.example.test",
    ABDM_ABHA_BASE_URL="https://abha.example.test/abha/api",
    ABDM_CLIENT_ID="test-client",
    ABDM_CLIENT_SECRET="test-secret-not-real",
    ABDM_CM_ID="sbx",
)
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY_B64 = base64.b64encode(PRIVATE_KEY.public_key().public_bytes(
    serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
)).decode()


def decrypt(value):
    return PRIVATE_KEY.decrypt(
        base64.b64decode(value),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None),
    ).decode()


class FakeABDM:
    """Answers like the ABDM sandbox and records every call."""

    def __init__(self, verified_number=ABHA, fail_status=None):
        self.verified_number = verified_number
        self.fail_status = fail_status
        self.calls = []

    def __call__(self, method, url, json=None, headers=None, timeout=None):
        self.calls.append({"method": method, "url": url, "json": json, "headers": headers})
        if self.fail_status:
            return self._reply({}, self.fail_status)
        if url.endswith("/sessions"):
            return self._reply({"accessToken": "sandbox-token", "expiresIn": 1200})
        if url.endswith("/public/certificate"):
            return self._reply({"publicKey": PUBLIC_KEY_B64})
        if url.endswith("/login/request/otp"):
            return self._reply({"txnId": "txn-123", "message": "OTP sent"})
        if url.endswith("/login/verify"):
            return self._reply({"authResult": "success", "accounts": [{
                "ABHANumber": self.verified_number, "preferredAbhaAddress": "asha@sbx",
                "name": "Asha Devi", "gender": "F", "yearOfBirth": "1985",
            }]})
        return self._reply({}, 404)

    @staticmethod
    def _reply(body, status_code=200):
        response = mock.Mock(status_code=status_code)
        response.json.return_value = body
        return response

    def call_to(self, suffix):
        return next(c for c in self.calls if c["url"].endswith(suffix))


@override_settings(**SANDBOX)
class ABHALinkTests(TestCase):
    def setUp(self):
        cache.clear()
        self.hospital = Hospital.objects.create(name="Synthetic ABDM Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Other Hospital", is_active=True)
        self.desk, _ = make_staff("abdm_desk", self.hospital, role=StaffRole.RECEPTIONIST)
        self.desk2, _ = make_staff("abdm_desk2", self.hospital, role=StaffRole.RECEPTIONIST)
        self.pharmacist, _ = make_staff("abdm_pharm", self.hospital, role=StaffRole.PHARMACIST)
        self.patient = self._patient("Asha Devi", "9000000051", self.hospital, "AB-1")
        self.twin = self._patient("Asha D", "9000000052", self.hospital, "AB-2")
        self.outsider = self._patient("Other", "9000000053", self.other, "OT-1")
        self.client = self._client(self.desk)

    @staticmethod
    def _patient(name, phone, hospital, uhid):
        patient = Patient.objects.create(name=name, age=40, gender="Female", phone=phone, hospital=hospital)
        PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=uhid)
        return patient

    def _client(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def _request_otp(self, fake, patient=None, abha=ABHA, client=None):
        with mock.patch("abdm.client.requests.request", side_effect=fake):
            return (client or self.client).post("/api/abdm/abha/request-otp/", {
                "patient": (patient or self.patient).id, "abha_number": abha, "otp_system": "aadhaar",
            }, format="json")

    def _confirm(self, fake, txn="txn-123", otp="123456", client=None):
        with mock.patch("abdm.client.requests.request", side_effect=fake):
            return (client or self.client).post("/api/abdm/abha/confirm-otp/", {"txn_id": txn, "otp": otp},
                                                format="json")

    # Switched off / not configured -------------------------------------------

    @override_settings(ABDM_ENABLED=False)
    def test_disabled_integration_is_not_found(self):
        self.assertEqual(self.client.get("/api/abdm/status/").status_code, 404)

    @override_settings(ABDM_CLIENT_ID="", ABDM_CLIENT_SECRET="")
    def test_missing_credentials_report_unavailable(self):
        status_body = self.client.get("/api/abdm/status/").json()
        self.assertFalse(status_body["configured"])
        self.assertNotIn("secret", json.dumps(status_body).lower())
        resp = self._request_otp(FakeABDM())
        self.assertEqual(resp.status_code, 503)
        self.assertIn("ABDM_CLIENT_ID", resp.json()["error"])

    # Happy path ----------------------------------------------------------------

    def test_verified_abha_is_linked_and_audited_without_secrets(self):
        fake = FakeABDM()
        resp = self._request_otp(fake)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["txn_id"], "txn-123")

        session = fake.call_to("/sessions")
        self.assertEqual(session["json"]["clientId"], "test-client")
        self.assertEqual(session["headers"]["X-CM-ID"], "sbx")
        otp_request = fake.call_to("/login/request/otp")
        self.assertEqual(decrypt(otp_request["json"]["loginId"]), "91123456789012")
        self.assertEqual(otp_request["headers"]["Authorization"], "Bearer sandbox-token")

        resp = self._confirm(fake)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(decrypt(fake.call_to("/login/verify")["json"]["authData"]["otp"]["otpValue"]), "123456")
        link = ABHALink.objects.get(patient=self.patient)
        self.assertEqual((link.abha_number, link.abha_address, link.verified_by), (ABHA, "asha@sbx", self.desk))
        self.assertEqual(resp.json()["abha_profile"]["year_of_birth"], "1985")

        audit = " ".join(AuditLog.objects.filter(action__startswith="abdm.").values_list("details", flat=True))
        self.assertIn("9012", audit)
        self.assertNotIn("5678", audit)
        self.assertNotIn("123456", audit)

        listed = self.client.get(f"/api/abdm/abha/links/?patient={self.patient.id}").json()
        self.assertEqual([row["abha_number"] for row in listed], [ABHA])

    # Refusals ------------------------------------------------------------------

    def test_input_and_scope_are_checked(self):
        self.assertEqual(self._request_otp(FakeABDM(), abha="12345").status_code, 400)
        self.assertEqual(self._request_otp(FakeABDM(), patient=self.outsider).status_code, 404)
        self.assertEqual(self._request_otp(FakeABDM(), client=self._client(self.pharmacist)).status_code, 403)

    def test_otp_check_is_bound_to_the_staff_member_who_started_it(self):
        fake = FakeABDM()
        self._request_otp(fake)
        self.assertEqual(self._confirm(fake, client=self._client(self.desk2)).status_code, 400)
        self.assertEqual(self._confirm(fake, txn="unknown").status_code, 400)
        self.assertEqual(self._confirm(fake, otp="12ab").status_code, 400)
        self.assertFalse(ABHALink.objects.exists())

    def test_different_abha_returned_by_abdm_is_not_linked(self):
        fake = FakeABDM(verified_number=OTHER_ABHA)
        self._request_otp(fake)
        self.assertEqual(self._confirm(fake).status_code, 409)
        self.assertFalse(ABHALink.objects.exists())

    def test_abha_already_linked_to_another_patient_is_refused(self):
        ABHALink.objects.create(patient=self.twin, hospital=self.hospital, abha_number=ABHA, otp_system="aadhaar")
        fake = FakeABDM()
        self._request_otp(fake)
        resp = self._confirm(fake)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("duplicate", resp.json()["error"])
        self.assertFalse(ABHALink.objects.filter(patient=self.patient).exists())

    def test_rejected_credentials_surface_as_bad_gateway(self):
        resp = self._request_otp(FakeABDM(fail_status=401))
        self.assertEqual(resp.status_code, 502)
        self.assertIn("credentials", resp.json()["error"])
        self.assertNotIn("test-secret-not-real", resp.content.decode())
