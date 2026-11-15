"""Family / caregiver (proxy) access: granted by the patient, read-only, own OTP.

SMS is replaced by the test cache delivery (PATIENT_OTP_DELIVERY="cache").
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient, PatientHospital, ProxyAccess
from security_tests.test_tenant_isolation import make_staff

User = get_user_model()
PROXY_PHONE = "9000000051"


def otp_for(phone):
    return cache.get(f"patient-otp:{phone}")


class ProxyAccessTests(TestCase):
    def setUp(self):
        cache.clear()
        self.hospital = Hospital.objects.create(name="Synthetic Proxy Hospital", is_active=True)
        self.patient = self._patient("Synthetic Kamla Devi", "9000000041", "kamla")
        self.other_patient = self._patient("Synthetic Other", "9000000042", "other")

    def _patient(self, name, phone, username):
        user = User.objects.create_user(username=username, password="Synthetic-Pass-123")
        patient = Patient.objects.create(
            user=user, name=name, age=70, gender="Female", phone=phone, hospital=self.hospital
        )
        PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid=f"UH-{username}")
        return patient

    def client_as(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        return client

    def grant(self, phone=PROXY_PHONE, patient=None):
        patient = patient or self.patient
        resp = self.client_as(patient.user).post(
            "/api/auth/patient/family-access/",
            {"name": "Synthetic Ravi", "relationship": "Son", "phone": phone},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()

    def proxy_sign_in(self, phone=PROXY_PHONE):
        client = APIClient(raise_request_exception=False)
        start = client.post("/api/auth/proxy/otp/request/", {"phone": phone}, format="json")
        self.assertEqual(start.status_code, 200, start.content)
        verify = client.post("/api/auth/proxy/otp/verify/", {"phone": phone, "otp": otp_for(phone)}, format="json")
        self.assertEqual(verify.status_code, 200, verify.content)
        body = verify.json()
        login = client.post(
            "/api/auth/proxy/login/", {"ticket": body["ticket"], "grant": body["grants"][0]["id"]}, format="json"
        )
        self.assertEqual(login.status_code, 200, login.content)
        session = APIClient(raise_request_exception=False)
        session.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        return session, login.json()

    # Granting -----------------------------------------------------------

    def test_patient_grants_lists_and_revokes_access(self):
        grant = self.grant()
        listed = self.client_as(self.patient.user).get("/api/auth/patient/family-access/")
        self.assertEqual([g["id"] for g in listed.json()], [grant["id"]])
        self.assertEqual(listed.json()[0]["relationship"], "Son")

        revoked = self.client_as(self.patient.user).post(f"/api/auth/patient/family-access/{grant['id']}/revoke/")
        self.assertEqual(revoked.status_code, 200, revoked.content)
        self.assertIsNotNone(ProxyAccess.objects.get(pk=grant["id"]).revoked_at)

    def test_staff_cannot_grant_family_access(self):
        staff, _ = make_staff("proxy_staff", self.hospital)
        resp = self.client_as(staff).post(
            "/api/auth/patient/family-access/",
            {"name": "X", "relationship": "Son", "phone": PROXY_PHONE},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_patient_cannot_revoke_another_patients_grant(self):
        grant = self.grant(patient=self.other_patient)
        resp = self.client_as(self.patient.user).post(f"/api/auth/patient/family-access/{grant['id']}/revoke/")
        self.assertEqual(resp.status_code, 404)
        self.assertIsNone(ProxyAccess.objects.get(pk=grant["id"]).revoked_at)

    def test_invalid_phone_rejected(self):
        resp = self.client_as(self.patient.user).post(
            "/api/auth/patient/family-access/",
            {"name": "Synthetic Ravi", "relationship": "Son", "phone": "12"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    # Signing in ---------------------------------------------------------

    def test_proxy_signs_in_and_sees_only_that_patient(self):
        self.grant()
        session, login = self.proxy_sign_in()
        self.assertEqual(login["patient"]["id"], self.patient.id)
        self.assertEqual(login["proxy"]["relationship"], "Son")

        me = session.get("/api/auth/patient/me/")
        self.assertEqual(me.status_code, 200, me.content)
        self.assertEqual(me.json()["patient"]["id"], self.patient.id)
        self.assertEqual(me.json()["proxy"]["name"], "Synthetic Ravi")

        patients = session.get("/api/patients/")
        body = patients.json()
        rows = body.get("results", body)
        self.assertEqual([row["id"] for row in rows], [self.patient.id])

    def test_proxy_is_read_only(self):
        self.grant()
        session, _ = self.proxy_sign_in()
        upload = session.post(f"/api/patients/{self.patient.id}/documents/", {"title": "x"}, format="json")
        self.assertEqual(upload.status_code, 403)
        regrant = session.post(
            "/api/auth/patient/family-access/",
            {"name": "Y", "relationship": "Friend", "phone": "9000000052"},
            format="json",
        )
        self.assertEqual(regrant.status_code, 403)
        self.assertEqual(ProxyAccess.objects.count(), 1)

    def test_proxy_is_read_only_under_the_versioned_prefix_too(self):
        self.grant()
        session, _ = self.proxy_sign_in()
        upload = session.post(f"/api/v1/patients/{self.patient.id}/documents/", {"title": "x"}, format="json")
        self.assertEqual(upload.status_code, 403)
        self.assertEqual(session.get("/api/v1/auth/patient/me/").status_code, 200)

    def test_revoked_access_stops_working_immediately(self):
        grant = self.grant()
        session, _ = self.proxy_sign_in()
        self.client_as(self.patient.user).post(f"/api/auth/patient/family-access/{grant['id']}/revoke/")
        resp = session.get("/api/patients/")
        self.assertEqual(resp.status_code, 401)

    def test_unknown_phone_gets_same_answer_and_no_code(self):
        self.grant()
        known = APIClient().post("/api/auth/proxy/otp/request/", {"phone": PROXY_PHONE}, format="json")
        unknown = APIClient().post("/api/auth/proxy/otp/request/", {"phone": "9000000059"}, format="json")
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.json()["message"], unknown.json()["message"])
        self.assertIsNone(otp_for("9000000059"))

    def test_wrong_otp_gives_no_ticket(self):
        self.grant()
        client = APIClient()
        client.post("/api/auth/proxy/otp/request/", {"phone": PROXY_PHONE}, format="json")
        resp = client.post("/api/auth/proxy/otp/verify/", {"phone": PROXY_PHONE, "otp": "000000"}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("ticket", resp.json())

    def test_ticket_cannot_open_another_phones_grant(self):
        mine = self.grant()
        theirs = self.grant(phone="9000000053", patient=self.other_patient)
        client = APIClient()
        client.post("/api/auth/proxy/otp/request/", {"phone": PROXY_PHONE}, format="json")
        verify = client.post("/api/auth/proxy/otp/verify/", {"phone": PROXY_PHONE, "otp": otp_for(PROXY_PHONE)}, format="json")
        self.assertEqual([g["id"] for g in verify.json()["grants"]], [mine["id"]])
        resp = client.post("/api/auth/proxy/login/", {"ticket": verify.json()["ticket"], "grant": theirs["id"]}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("access", resp.json())
