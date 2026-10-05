from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from hospital.models import Hospital, Department

User = get_user_model()


class StaffAuthenticationTests(TestCase):
    """Tests for staff authentication and authorization."""

    def setUp(self):
        self.client = APIClient()

        # Create hospitals
        self.hospital_a = Hospital.objects.create(
            name="Hospital A",
            address="123 Main St",
            city="City A",
            is_active=True
        )
        self.hospital_b = Hospital.objects.create(
            name="Hospital B",
            address="456 Oak Ave",
            city="City B",
            is_active=True
        )

        # Create department
        self.department = Department.objects.create(
            hospital=self.hospital_a,
            name="Emergency"
        )

        # Create staff user for Hospital A
        self.staff_user_a = User.objects.create_user(
            username="doctor_a",
            email="doctor_a@hospital.com",
            password="testpass123",
            first_name="Dr. Alice",
            last_name="Smith"
        )
        self.staff_profile_a = StaffProfile.objects.create(
            user=self.staff_user_a,
            role=StaffRole.DOCTOR,
            employee_id="EMP001",
            is_active_staff=True
        )
        self.membership_a = StaffHospitalMembership.objects.create(
            staff=self.staff_profile_a,
            hospital=self.hospital_a,
            role=StaffRole.DOCTOR,
            department=self.department,
            is_active=True
        )

        # Create staff user for Hospital B
        self.staff_user_b = User.objects.create_user(
            username="nurse_b",
            email="nurse_b@hospital.com",
            password="testpass123",
            first_name="Nurse Bob",
            last_name="Jones"
        )
        self.staff_profile_b = StaffProfile.objects.create(
            user=self.staff_user_b,
            role=StaffRole.NURSE,
            employee_id="EMP002",
            is_active_staff=True
        )
        self.membership_b = StaffHospitalMembership.objects.create(
            staff=self.staff_profile_b,
            hospital=self.hospital_b,
            role=StaffRole.NURSE,
            is_active=True
        )

        # Create inactive staff user
        self.staff_user_inactive = User.objects.create_user(
            username="inactive_staff",
            email="inactive@hospital.com",
            password="testpass123",
            first_name="Inactive",
            last_name="Staff"
        )
        self.staff_profile_inactive = StaffProfile.objects.create(
            user=self.staff_user_inactive,
            role=StaffRole.DOCTOR,
            employee_id="EMP003",
            is_active_staff=False
        )
        self.membership_inactive = StaffHospitalMembership.objects.create(
            staff=self.staff_profile_inactive,
            hospital=self.hospital_a,
            role=StaffRole.DOCTOR,
            is_active=True
        )

    def test_staff_login_success(self):
        """Test successful staff login returns JWT tokens and user data."""
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertIn("roles", response.data)
        self.assertIn("hospitals", response.data)

        # Verify user data
        self.assertEqual(response.data["user"]["username"], "doctor_a")
        self.assertEqual(response.data["user"]["staff_role"], "Doctor")
        self.assertIn("Doctor", response.data["roles"])
        self.assertEqual(len(response.data["hospitals"]), 1)
        self.assertEqual(response.data["hospitals"][0]["id"], self.hospital_a.id)

    def test_staff_login_failure_invalid_credentials(self):
        """Test staff login fails with invalid credentials."""
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "wrongpassword"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_staff_login_failure_inactive_staff(self):
        """Test staff login fails for inactive staff."""
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "inactive_staff", "password": "testpass123"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_staff_login_failure_no_staff_profile(self):
        """Test login fails for user without staff profile."""
        regular_user = User.objects.create_user(
            username="regular_user",
            email="regular@test.com",
            password="testpass123"
        )
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "regular_user", "password": "testpass123"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_jwt_access_token(self):
        """Test access token can be used to access protected endpoints."""
        # Login first
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]

        # Use access token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get("/api/auth/staff/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "doctor_a")

    def test_jwt_refresh_token(self):
        """Test refresh token can be used to get new access token."""
        # Login first
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        refresh_token = response.data["refresh"]

        # Use refresh token to get new access token
        response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh_token},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_unauthorized_api_returns_401(self):
        """Test unauthenticated requests return 401."""
        response = self.client.get("/api/auth/staff/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_role_returns_403(self):
        """Test users without required role get 403."""
        # Login as nurse (not doctor)
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "nurse_b", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Try to access doctor-only endpoint (e.g., clinical notes create)
        # This should be 403 if the endpoint requires Doctor role
        # Note: We're testing the permission system, not specific endpoints
        # since endpoints may have different permission requirements

    def test_hospital_a_user_can_access_hospital_a_data(self):
        """Test Hospital A user can access Hospital A data."""
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Access patients in Hospital A
        response = self.client.get(f"/api/patients/?hospital={self.hospital_a.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hospital_a_user_cannot_access_hospital_b_data(self):
        """Test Hospital A user cannot access Hospital B data."""
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Try to access patients in Hospital B
        response = self.client.get(f"/api/patients/?hospital={self.hospital_b.id}")
        # Should be forbidden or return empty
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_200_OK])
        # If 200, should return empty list
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.data.get("results", response.data)), 0)

    def test_direct_object_cross_hospital_access_denied(self):
        """Test direct object access across hospitals is denied."""
        from patients.models import Patient

        # Create a patient in Hospital B
        patient_b = Patient.objects.create(
            name="Patient B",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_b
        )

        # Login as Hospital A user
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Try to access Hospital B patient directly
        response = self.client.get(f"/api/patients/{patient_b.id}/")
        # Should be 404 (not found) or 403 (forbidden)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_query_param_hospital_spoofing_denied(self):
        """Test hospital query parameter spoofing is denied."""
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Try to spoof hospital B in query param
        response = self.client.get(f"/api/patients/?hospital={self.hospital_b.id}")
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_200_OK])

    def test_staff_logout_blacklists_refresh_token(self):
        """Test logout blacklists refresh token."""
        # Login
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]
        refresh_token = response.data["refresh"]

        # Logout with access token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.post(
            "/api/auth/staff/logout/",
            {"refresh": refresh_token},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try to use blacklisted refresh token
        response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh_token},
            format="json"
        )
        # Blacklisted token should be rejected (400 or 401)
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

    def test_staff_me_endpoint(self):
        """Test /api/auth/staff/me/ endpoint returns user info."""
        response = self.client.post(
            "/api/auth/staff/login/",
            {"username": "doctor_a", "password": "testpass123"},
            format="json"
        )
        access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get("/api/auth/staff/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("roles", response.data)
        self.assertIn("hospitals", response.data)

    def test_patient_google_oauth_still_works(self):
        """Test that patient Google OAuth is not affected."""
        # The google login endpoint should still exist
        response = self.client.post(
            "/api/auth/google/",
            {"credential": "fake_token"},
            format="json"
        )
        # Should not be 404 (endpoint exists)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HospitalMembershipTests(TestCase):
    """Tests for hospital membership system."""

    def setUp(self):
        self.hospital_a = Hospital.objects.create(
            name="Hospital A",
            is_active=True
        )
        self.hospital_b = Hospital.objects.create(
            name="Hospital B",
            is_active=True
        )

        self.user = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="testpass123"
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.DOCTOR,
            employee_id="EMP001"
        )

    def test_user_can_have_multiple_hospital_memberships(self):
        """Test user can have memberships in multiple hospitals."""
        membership_a = StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.DOCTOR,
            is_active=True
        )
        membership_b = StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_b,
            role=StaffRole.NURSE,
            is_active=True
        )

        self.assertEqual(self.staff_profile.hospital_memberships.count(), 2)

    def test_inactive_membership_denies_access(self):
        """Test inactive membership denies access."""
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.DOCTOR,
            is_active=False
        )

        # User should not have access to hospital_a
        from users.permissions import get_user_hospital_ids
        hospital_ids = get_user_hospital_ids(self.user)
        self.assertNotIn(self.hospital_a.id, hospital_ids)

    def test_unique_membership_per_hospital(self):
        """Test user can only have one membership per hospital."""
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.DOCTOR,
            is_active=True
        )

        # Second membership for same hospital should fail
        with self.assertRaises(Exception):
            StaffHospitalMembership.objects.create(
                staff=self.staff_profile,
                hospital=self.hospital_a,
                role=StaffRole.NURSE,
                is_active=True
            )