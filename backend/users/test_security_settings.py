"""Read-only security settings screen (A14)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from hospital.models import Hospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
URL = "/api/auth/security-settings/"


def staff(username, hospital, role):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=username, is_active_staff=True)
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user


class SecuritySettingsTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Hospital A", is_active=True)
        self.client = APIClient()

    def get(self, user):
        self.client.force_authenticate(user=user)
        return self.client.get(URL, HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

    @override_settings(STAFF_LOGIN_REQUIRE_OTP=True, DEV_LOGIN_ENABLED=False)
    def test_admin_sees_effective_values_read_only(self):
        response = self.get(staff("admin", self.hospital, StaffRole.ADMIN))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["editable"])
        rows = {row["key"]: row for row in response.data["settings"]}
        self.assertEqual((rows["STAFF_LOGIN_REQUIRE_OTP"]["value"], rows["STAFF_LOGIN_REQUIRE_OTP"]["secure"]), (True, True))
        self.assertEqual(rows["DEV_LOGIN_ENABLED"]["secure"], True)

    def test_no_secret_is_returned(self):
        response = self.get(staff("admin", self.hospital, StaffRole.ADMIN))

        text = str(response.data).upper()
        for secret_word in ("SECRET", "PASSWORD\":", "SIGNING_KEY", "API_KEY", "TOKEN\":"):
            self.assertNotIn(secret_word, text)

    def test_other_roles_are_refused(self):
        for role in (StaffRole.DOCTOR, StaffRole.HOSPITAL_MANAGER, StaffRole.RECEPTIONIST):
            response = self.get(staff(f"u_{role}".lower().replace(" ", "_"), self.hospital, role))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, role)

    def test_cannot_be_changed_over_the_api(self):
        self.client.force_authenticate(user=staff("admin", self.hospital, StaffRole.ADMIN))

        response = self.client.post(URL, {"DEBUG": True}, format="json", HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
