"""
Regression tests for the low findings S-L1 to S-L8 of the 2026-11-18
production readiness audit (docs/PRODUCTION_READINESS_AUDIT_2026-11-18.md).
All data is synthetic.
"""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from ai_scribe import audio_validation
from ai_scribe.models import AIPromptTemplate, ClinicalExtractionSchema, ConsultationSession
from audit.models import AuditLog
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from pharmacy.models import Medicine
from users.models import DeviceSession, StaffHospitalMembership, StaffProfile, StaffRole
from users.staff_invite import EMAIL_NOT_INVITABLE
from users.views import LOCKED_OUT_MESSAGE, REGISTRATION_UNAVAILABLE

from .test_tenant_isolation import make_staff

User = get_user_model()
PASSWORD = "synthetic-Pass-123"
WRONG = "wrong-Pass-999"
WEBM = b"\x1a\x45\xdf\xa3synthetic-webm"
M4A = b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00synthetic"


def client_for(user=None, hospital=None):
    client = APIClient(raise_request_exception=False)
    if user is not None:
        client.force_authenticate(user)
    if hospital is not None:
        client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
    return client


@override_settings(RATE_LIMIT_ENABLED=False, STAFF_LOGIN_REQUIRE_OTP=False)
class StaffLockoutPerAccountTests(TestCase):
    """S-L2: the username and the email of one account share one failure budget."""

    URL = "/api/auth/staff/login/"

    def setUp(self):
        cache.clear()
        self.hospital = Hospital.objects.create(name="Synthetic Lockout Hospital", is_active=True)
        self.user, _ = make_staff("rao_synthetic", self.hospital, role=StaffRole.NURSE)
        self.user.email = "rao.synthetic@example.org"
        self.user.save(update_fields=["email"])
        self.client = client_for()

    def _login(self, identifier, password):
        return self.client.post(self.URL, {"username": identifier, "password": password}, format="json")

    def test_failures_by_username_and_email_lock_the_same_account(self):
        for _ in range(3):
            self.assertEqual(self._login("rao_synthetic", WRONG).status_code, 401)
        for _ in range(2):
            self.assertEqual(self._login("RAO.SYNTHETIC@example.org", WRONG).status_code, 401)

        # Before S-L2 each identifier had its own budget, so this returned 200.
        locked = self._login("rao_synthetic", PASSWORD)
        self.assertEqual(locked.status_code, 429)
        self.assertEqual(locked.json()["error"], LOCKED_OUT_MESSAGE)
        self.assertEqual(self._login("rao.synthetic@example.org", PASSWORD).status_code, 429)
        self.assertTrue(AuditLog.objects.filter(action="auth.staff_login.locked").exists())

    def test_an_unknown_identifier_locks_the_same_way(self):
        for _ in range(5):
            self._login("nobody_synthetic", WRONG)
        self.assertEqual(self._login("nobody_synthetic", WRONG).json()["error"], LOCKED_OUT_MESSAGE)

    def test_a_correct_password_before_the_limit_clears_the_account_counter(self):
        for _ in range(4):
            self._login("rao.synthetic@example.org", WRONG)
        self.assertEqual(self._login("rao_synthetic", PASSWORD).status_code, 200)
        for _ in range(4):
            self.assertEqual(self._login("rao_synthetic", WRONG).status_code, 401)
        self.assertEqual(self._login("rao_synthetic", PASSWORD).status_code, 200)


@override_settings(RATE_LIMIT_ENABLED=False)
class PatientLockoutTests(TestCase):
    """S-L1: patient password sign-in locks per account, not only per address."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("asha_synthetic", email="asha.synthetic@example.com", password=PASSWORD)
        self.patient = Patient.objects.create(
            user=self.user, name="Asha Synthetic", age=34, gender="Female", phone="9811100001",
            email_verified=True, status="Active",
        )
        self.client = client_for()

    def _email_login(self, password, email="asha.synthetic@example.com"):
        return self.client.post("/api/auth/patient/login/", {"email": email, "password": password}, format="json")

    def _token_login(self, password, identifier="9811100001"):
        return self.client.post("/api/auth/patient/token/", {"identifier": identifier, "password": password},
                                format="json")

    def test_five_wrong_passwords_lock_email_sign_in(self):
        for _ in range(5):
            self.assertEqual(self._email_login(WRONG).status_code, 401)
        # Before S-L1 this was 200: only the per-address limit existed.
        locked = self._email_login(PASSWORD)
        self.assertEqual(locked.status_code, 429)
        self.assertEqual(locked.json()["error"], LOCKED_OUT_MESSAGE)

    def test_failures_by_mobile_number_lock_email_sign_in_too(self):
        for _ in range(5):
            self.assertEqual(self._token_login(WRONG).status_code, 401)
        self.assertEqual(self._token_login(PASSWORD).status_code, 429)
        self.assertEqual(self._email_login(PASSWORD).status_code, 429)

    def test_an_unknown_email_locks_with_the_same_reply(self):
        for _ in range(5):
            self._email_login(WRONG, email="nobody.synthetic@example.com")
        self.assertEqual(self._email_login(WRONG, email="nobody.synthetic@example.com").json()["error"],
                         LOCKED_OUT_MESSAGE)

    def test_correct_password_still_signs_in_below_the_limit(self):
        for _ in range(4):
            self._email_login(WRONG)
        self.assertEqual(self._email_login(PASSWORD).status_code, 200)


class LegacyMedicineIsolationTests(TestCase):
    """S-L3: stock with no hospital is never sold or dispensed, and new stock needs one."""

    def setUp(self):
        self.hospital_a = Hospital.objects.create(name="Synthetic Pharmacy A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Synthetic Pharmacy B", is_active=True)
        self.pharmacist, _ = make_staff("pharm_synthetic", self.hospital_a, role=StaffRole.PHARMACIST)
        self.legacy = Medicine.objects.create(name="Legacy Synthetic", hospital=None, category="Tablet",
                                              price="10.00", quantity=50)

    def test_a_hospital_less_medicine_cannot_be_sold(self):
        response = client_for(self.pharmacist, self.hospital_a).post("/api/pharmacy-sales/", {
            "medicine": self.legacy.id, "patient_name": "Synthetic Buyer", "quantity": 5,
            "hospital": self.hospital_a.id,
        }, format="json")
        # Before S-L3 this was 201 and drew down stock no hospital owns.
        self.assertEqual(response.status_code, 400, response.content)
        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.quantity, 50)

    def test_new_stock_must_belong_to_a_hospital(self):
        StaffHospitalMembership.objects.create(
            staff=StaffProfile.objects.get(user=self.pharmacist), hospital=self.hospital_b,
            role=StaffRole.PHARMACIST, is_active=True,
        )
        response = client_for(self.pharmacist).post("/api/pharmacy/", {
            "name": "Orphan Synthetic", "category": "Tablet", "price": "5.00", "quantity": 10,
        }, format="json")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Medicine.objects.filter(name="Orphan Synthetic").exists())


@override_settings(RATE_LIMIT_ENABLED=False)
class EnumerationTests(TestCase):
    """S-L4: registration and staff invitation replies do not reveal who has an account."""

    def setUp(self):
        self.hospital_a = Hospital.objects.create(name="Synthetic Invite A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Synthetic Invite B", is_active=True)
        self.admin_a, _ = make_staff("invite_admin_a", self.hospital_a, role=StaffRole.ADMIN)
        self.admin_b, _ = make_staff("invite_admin_b", self.hospital_b, role=StaffRole.ADMIN)
        patient_user = User.objects.create_user("pat_synthetic", email="pat.synthetic@example.com", password=PASSWORD)
        Patient.objects.create(user=patient_user, name="Pat Synthetic", age=40, gender="Male", phone="9811100002")

    def _register(self, **fields):
        payload = {"role": "Patient", "full_name": "New Synthetic", "phone": "9811100099",
                   "email": "new.synthetic@example.com", "password": "correct-horse-9",
                   "confirm_password": "correct-horse-9"}
        payload.update(fields)
        return client_for().post("/api/auth/register/", payload, format="json")

    def test_taken_email_and_taken_mobile_get_the_same_reply(self):
        by_email = self._register(email="pat.synthetic@example.com")
        by_phone = self._register(phone="9811100002")
        self.assertEqual(by_email.status_code, 400)
        self.assertEqual(by_email.json()["error"], REGISTRATION_UNAVAILABLE)
        self.assertEqual(by_phone.json()["error"], by_email.json()["error"])

    def _invite(self, admin, hospital, email):
        return client_for(admin, hospital).post("/api/users/invite/", {
            "name": "Invited Synthetic", "phone": "9811100003", "email": email, "role": StaffRole.NURSE,
        }, format="json")

    def test_patient_email_and_another_hospitals_pending_invite_look_the_same(self):
        patient_reply = self._invite(self.admin_a, self.hospital_a, "pat.synthetic@example.com")
        self.assertEqual(self._invite(self.admin_b, self.hospital_b, "pending.synthetic@example.com").status_code, 201)
        pending_reply = self._invite(self.admin_a, self.hospital_a, "pending.synthetic@example.com")
        self.assertEqual(patient_reply.status_code, 400)
        self.assertEqual(pending_reply.status_code, 400)
        self.assertEqual(patient_reply.json(), pending_reply.json())
        self.assertNotIn("patient", str(patient_reply.json()).lower())


class SecurityOverviewScopeTests(TestCase):
    """S-L5: an Admin sees only this hospital's (and account-wide) sign-in records."""

    URL = "/api/hospital/security-overview/"

    def setUp(self):
        self.hospital_a = Hospital.objects.create(name="Synthetic Overview A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Synthetic Overview B", is_active=True)
        self.admin_a, _ = make_staff("ov_admin_a", self.hospital_a, role=StaffRole.ADMIN)
        self.shared, profile = make_staff("ov_shared", self.hospital_a, role=StaffRole.DOCTOR)
        StaffHospitalMembership.objects.create(staff=profile, hospital=self.hospital_b, role=StaffRole.DOCTOR,
                                               is_active=True)
        self.former, former_profile = make_staff("ov_former", self.hospital_a, role=StaffRole.NURSE)
        StaffHospitalMembership.objects.filter(staff=former_profile).update(is_active=False)
        for user in (self.shared, self.former):
            DeviceSession.objects.create(user=user, account_type="staff", platform="android",
                                         device_id=f"device-{user.username}")
        AuditLog.objects.create(user=self.shared, action="auth.staff_login.success")
        AuditLog.objects.create(user=self.shared, hospital=self.hospital_b, action="auth.proxy.login")
        AuditLog.objects.create(user=self.shared, hospital=self.hospital_b, action="auth.refresh_reuse")
        AuditLog.objects.create(user=self.former, action="auth.staff_login.success")

    def test_other_hospitals_rows_former_members_and_device_ids_are_left_out(self):
        response = client_for(self.admin_a, self.hospital_a).get(self.URL)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual([row["action"] for row in body["sign_in_history"]], ["auth.staff_login.success"])
        self.assertEqual({row["user_id"] for row in body["sign_in_history"]}, {self.shared.id})
        self.assertNotIn("refresh_reuse", {alert["kind"] for alert in body["alerts"]})
        self.assertEqual({row["user_id"] for row in body["sessions"]}, {self.shared.id})
        self.assertNotIn("device_id", response.content.decode())
        self.assertNotIn("device-ov_", response.content.decode())


class AudioSignatureUnitTests(SimpleTestCase):
    """S-L6: the container is read from the bytes."""

    def test_known_signatures(self):
        self.assertEqual(audio_validation.sniff_container(b"RIFF\x00\x00\x00\x00WAVEfmt "), "wav")
        self.assertEqual(audio_validation.sniff_container(b"ID3\x04"), "mp3")
        self.assertEqual(audio_validation.sniff_container(b"\xff\xfb\x90\x00"), "mp3")
        self.assertEqual(audio_validation.sniff_container(M4A), "mp4")
        self.assertEqual(audio_validation.sniff_container(b"OggS\x00\x02"), "ogg")
        self.assertEqual(audio_validation.sniff_container(WEBM), "webm")
        for not_audio in (b"<script>alert(1)</script>", b"%PDF-1.7", b"\x89PNG\r\n\x1a\n", b"MZ\x90\x00", b""):
            self.assertIsNone(audio_validation.sniff_container(not_audio), not_audio)


MEDIA = tempfile.mkdtemp(prefix="hms-sl6-")


@override_settings(MEDIA_ROOT=MEDIA, RATE_LIMIT_ENABLED=False)
class AudioUploadValidationTests(TestCase):
    """S-L6: uploads are checked by content and stored under a server-chosen name."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Audio Hospital", is_active=True)
        self.user, _ = make_staff("audio_doctor", self.hospital, role=StaffRole.DOCTOR)
        doctor = Doctor.objects.create(hospital=self.hospital, user=self.user, name="Dr Audio Synthetic",
                                       specialization="General", phone="9000000031")
        patient = Patient.objects.create(name="Audio Synthetic", age=50, gender="Male", phone="9000000032",
                                         hospital=self.hospital)
        PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid="AUD-1")
        visit = Visit.objects.create(patient=patient, hospital=self.hospital, doctor=doctor)
        self.client = client_for(self.user, self.hospital)
        created = self.client.post("/api/ai/consultation-sessions/", {
            "visit": visit.id, "hospital": self.hospital.id, "patient": patient.id, "doctor": doctor.id,
            "language": "en",
        }, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        self.session_id = created.json()["id"]
        self.base = f"/api/ai/consultation-sessions/{self.session_id}"

    def _upload(self, name, data, content_type):
        audio = SimpleUploadedFile(name, data, content_type=content_type)
        return self.client.post(f"{self.base}/upload_audio/", {"audio_file": audio}, format="multipart")

    def test_html_labelled_as_audio_is_refused(self):
        # Before S-L6 this was 200: only the client's Content-Type was checked.
        self.assertEqual(self._upload("x.html", b"<html><script>alert(1)</script>", "audio/webm").status_code, 400)

    def test_content_must_match_the_declared_format(self):
        self.assertEqual(self._upload("c.webm", M4A, "audio/webm").status_code, 400)

    def test_real_audio_is_stored_under_a_server_name(self):
        response = self._upload("../../evil.html", WEBM, "audio/webm;codecs=opus")
        self.assertEqual(response.status_code, 200, response.content)
        stored = ConsultationSession.objects.get(pk=self.session_id).audio_file.name
        self.assertTrue(stored.endswith(".webm"), stored)
        self.assertNotIn("evil", stored)


class LegacyProfileReactivationTests(TestCase):
    """S-L7: an invitation never admits an old self-signup account with its old password."""

    def setUp(self):
        cache.clear()
        self.hospital = Hospital.objects.create(name="Synthetic Legacy Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Legacy Other", is_active=True)
        self.admin, _ = make_staff("legacy_admin", self.hospital, role=StaffRole.ADMIN)
        self.legacy = User.objects.create_user("legacy_synthetic", email="legacy.synthetic@example.org",
                                               password=PASSWORD)
        self.profile = StaffProfile.objects.create(user=self.legacy, role=StaffRole.NURSE, employee_id="EMP-LEG",
                                                   phone="9811100004", is_active_staff=False)

    def _invite(self):
        return client_for(self.admin, self.hospital).post("/api/users/invite/", {
            "name": "Legacy Synthetic", "phone": "9811100004", "email": "legacy.synthetic@example.org",
            "role": StaffRole.NURSE,
        }, format="json")

    def test_the_old_password_is_discarded_and_a_set_password_link_is_issued(self):
        DeviceSession.objects.create(user=self.legacy, account_type="staff", platform="web")
        response = self._invite()
        self.assertEqual(response.status_code, 201, response.content)
        self.legacy.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_active_staff)
        # Before S-L7 the self-chosen password kept working.
        self.assertFalse(self.legacy.has_usable_password())
        self.assertTrue(response.json()["invited"])
        self.assertIn("/staff-invite/", response.json()["invite_url"])
        self.assertFalse(DeviceSession.objects.filter(user=self.legacy, revoked_at__isnull=True).exists())
        self.assertTrue(AuditLog.objects.filter(action="users.staff.legacy_readmitted").exists())

    def test_an_inactive_profile_held_by_another_hospital_is_not_reactivated(self):
        StaffHospitalMembership.objects.create(staff=self.profile, hospital=self.other, role=StaffRole.NURSE,
                                               is_active=True)
        response = self._invite()
        self.assertEqual(response.status_code, 400)
        self.assertIn(EMAIL_NOT_INVITABLE, response.content.decode())
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_active_staff)
        self.legacy.refresh_from_db()
        self.assertTrue(self.legacy.check_password(PASSWORD))


class AIConfigurationWriteTests(TestCase):
    """S-L8: platform-wide schemas and prompts cannot be written by a hospital's doctor."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic AI Config", is_active=True)
        self.doctor, _ = make_staff("ai_cfg_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.schema = ClinicalExtractionSchema.objects.create(version="v-synthetic", name="Synthetic", schema={})
        self.prompt = AIPromptTemplate.objects.create(version="p-synthetic", name="Synthetic",
                                                      system_prompt="s", user_prompt_template="u")

    def test_writes_are_refused_and_reads_work(self):
        client = client_for(self.doctor, self.hospital)
        for url, obj in (("/api/ai/schemas/", self.schema), ("/api/ai/prompts/", self.prompt)):
            created = client.post(url, {"version": "x", "name": "x", "schema": {}, "system_prompt": "x",
                                        "user_prompt_template": "x"}, format="json")
            # Before S-L8 a doctor's POST created a platform-wide row (201).
            self.assertEqual(created.status_code, 405, url)
            self.assertEqual(client.patch(f"{url}{obj.pk}/", {"name": "y"}, format="json").status_code, 405, url)
            self.assertEqual(client.delete(f"{url}{obj.pk}/").status_code, 405, url)
            self.assertEqual(client.get(url).status_code, 200, url)
        self.assertEqual(ClinicalExtractionSchema.objects.count(), 1)
        self.assertEqual(AIPromptTemplate.objects.count(), 1)
