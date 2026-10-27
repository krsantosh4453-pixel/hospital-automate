"""Inviting staff: the Admin/Manager creates the membership, the person sets a password from the link."""

import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from hospital.models import Department, Hospital
from patients.models import Patient
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
STRONG = "Ward-Round-2026!"


def make_staff(username, memberships, email=""):
    user = User.objects.create_user(username=username, password="testpass123", email=email)
    profile = StaffProfile.objects.create(user=user, role=memberships[0][1], employee_id=f"EMP-{username}", is_active_staff=True)
    for hospital, role in memberships:
        StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", FRONTEND_URL="https://hms.test")
class StaffInviteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="City Care", is_active=True)
        self.other = Hospital.objects.create(name="Other", is_active=True)
        self.cardio = Department.objects.create(hospital=self.hospital, name="Cardiology")
        self.admin = make_staff("admin", [(self.hospital, StaffRole.ADMIN)])
        self.manager = make_staff("manager", [(self.hospital, StaffRole.HOSPITAL_MANAGER)])
        self.client.force_authenticate(user=self.admin)

    def _invite(self, **data):
        body = {"name": "Asha Verma", "phone": "+91 98765 43210", "email": "asha@example.com", "role": "Doctor", **data}
        return self.client.post(f"/api/users/invite/?hospital={self.hospital.id}", body, format="json")

    def _link_parts(self, url):
        return re.search(r"/staff-invite/([^/]+)/([^/]+)$", url).groups()

    def test_invite_creates_account_membership_and_link(self):
        resp = self._invite(department=self.cardio.id)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        user = User.objects.get(email="asha@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.staff_profile.phone, "9876543210")
        membership = StaffHospitalMembership.objects.get(staff__user=user, hospital=self.hospital)
        self.assertEqual((membership.role, membership.department_id), ("Doctor", self.cardio.id))
        self.assertTrue(resp.data["invite_url"].startswith("https://hms.test/staff-invite/"))
        self.assertTrue(resp.data["invite_pending"])
        self.assertTrue(resp.data["emailed"])
        self.assertIn(resp.data["invite_url"], mail.outbox[0].body)

    def test_person_sets_password_once_then_link_is_dead(self):
        uid, token = self._link_parts(self._invite().data["invite_url"])
        anon = APIClient()
        info = anon.get(f"/api/auth/staff/invite/{uid}/{token}/")
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.data["hospitals"], [{"name": "City Care", "role": "Doctor"}])
        resp = anon.post(f"/api/auth/staff/invite/{uid}/{token}/", {"password": STRONG, "confirm_password": STRONG}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(User.objects.get(email="asha@example.com").check_password(STRONG))
        again = anon.post(f"/api/auth/staff/invite/{uid}/{token}/", {"password": STRONG, "confirm_password": STRONG}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_weak_or_mismatched_password_is_refused(self):
        uid, token = self._link_parts(self._invite().data["invite_url"])
        url = f"/api/auth/staff/invite/{uid}/{token}/"
        self.assertEqual(APIClient().post(url, {"password": STRONG, "confirm_password": "x"}, format="json").status_code, 400)
        self.assertEqual(APIClient().post(url, {"password": "123", "confirm_password": "123"}, format="json").status_code, 400)

    def test_tampered_token_is_refused(self):
        uid, _ = self._link_parts(self._invite().data["invite_url"])
        self.assertEqual(APIClient().get(f"/api/auth/staff/invite/{uid}/bad-token/").status_code, 400)

    def test_link_cannot_reset_an_existing_password(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.manager.pk))
        token = default_token_generator.make_token(self.manager)
        self.assertEqual(APIClient().get(f"/api/auth/staff/invite/{uid}/{token}/").status_code, 400)

    def test_existing_staff_elsewhere_is_added_without_a_link(self):
        make_staff("nurse", [(self.other, StaffRole.NURSE)], email="nurse@example.com")
        resp = self._invite(email="nurse@example.com", role="Nurse")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertFalse(resp.data["invited"])
        self.assertNotIn("invite_url", resp.data)
        self.assertEqual(StaffHospitalMembership.objects.filter(staff__user__email="nurse@example.com").count(), 2)

    def test_patient_email_or_existing_member_is_refused(self):
        patient_user = User.objects.create_user(username="pat", email="pat@example.com", password="x-Long-pass-1")
        Patient.objects.create(user=patient_user, name="Pat", age=30, gender="Male", phone="9000000009")
        self.assertEqual(self._invite(email="pat@example.com").status_code, 400)
        self.assertEqual(self._invite().status_code, 201)
        self.assertEqual(self._invite().status_code, 400)

    def test_bad_input_is_refused(self):
        self.assertEqual(self._invite(phone="123").status_code, 400)
        self.assertEqual(self._invite(name="").status_code, 400)
        self.assertEqual(self._invite(role="Wizard").status_code, 400)
        self.assertEqual(self._invite(department=999999).status_code, 400)
        self.assertFalse(User.objects.filter(email="asha@example.com").exists())

    def test_only_admin_grants_admin_and_doctors_cannot_invite(self):
        self.client.force_authenticate(user=self.manager)
        self.assertEqual(self._invite(role="Admin").status_code, 403)
        self.assertEqual(self._invite(role="Receptionist").status_code, 201)
        doctor = make_staff("doc", [(self.hospital, StaffRole.DOCTOR)])
        self.client.force_authenticate(user=doctor)
        self.assertEqual(self._invite(email="x@example.com").status_code, 403)

    def test_cannot_invite_into_a_hospital_you_do_not_manage(self):
        resp = self.client.post(f"/api/users/invite/?hospital={self.other.id}",
                                {"name": "X", "phone": "9876500000", "role": "Nurse"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_resend_gives_a_new_link_until_password_set(self):
        user_id = self._invite().data["id"]
        resp = self.client.post(f"/api/users/{user_id}/invite/?hospital={self.hospital.id}")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("/staff-invite/", resp.data["invite_url"])
        self.assertEqual(self.client.post(f"/api/users/{self.manager.id}/invite/?hospital={self.hospital.id}").status_code, 400)

    def test_staff_list_marks_pending_invites(self):
        self._invite()
        rows = {r["email"]: r for r in self.client.get(f"/api/users/?hospital={self.hospital.id}").data["staff"]}
        self.assertTrue(rows["asha@example.com"]["invite_pending"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", FRONTEND_URL="",
                   CSRF_TRUSTED_ORIGINS=["http://app.test:5173"])
class InviteLinkAddressTests(TestCase):
    """Without FRONTEND_URL the link points at the web app the inviter uses, if that origin is trusted."""

    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="City Care", is_active=True)
        self.client.force_authenticate(user=make_staff("admin", [(self.hospital, StaffRole.ADMIN)]))

    def _invite(self, origin):
        return self.client.post(f"/api/users/invite/?hospital={self.hospital.id}",
                                {"name": "Ravi", "phone": "9876500001", "role": "Nurse"},
                                format="json", HTTP_ORIGIN=origin)

    def test_trusted_origin_is_used(self):
        data = self._invite("http://app.test:5173").data
        self.assertTrue(data["invite_url"].startswith("http://app.test:5173/staff-invite/"))
        self.assertTrue(data["invite_url"].endswith(data["invite_path"]))

    def test_untrusted_origin_is_ignored(self):
        self.assertTrue(self._invite("https://evil.example").data["invite_url"].startswith("http://testserver/staff-invite/"))
