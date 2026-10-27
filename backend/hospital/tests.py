"""Tests for hospital module."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department, Ward, Room, Bed
from users.models import StaffProfile, StaffHospitalMembership, StaffRole

User = get_user_model()


class HospitalAPITests(TestCase):
    """Tests for hospital API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(
            name="Hospital A",
            address="123 Main St",
            city="City A",
            phone="1234567890",
            email="hospital_a@test.com",
            is_active=True,
        )
        self.hospital_b = Hospital.objects.create(
            name="Hospital B",
            address="456 Oak Ave",
            city="City B",
            phone="0987654321",
            email="hospital_b@test.com",
            is_active=True,
        )

        # Create superuser for hospital management
        self.user = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@test.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.ADMIN,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.ADMIN,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

    def _get_hospitals_url(self):
        return "/api/hospital/hospitals/"

    def _get_departments_url(self):
        return f"/api/hospital/departments/?hospital={self.hospital_a.id}"

    def _get_wards_url(self):
        return f"/api/hospital/wards/?hospital={self.hospital_a.id}"

    def test_list_hospitals(self):
        """Test listing hospitals (superuser sees all)."""
        response = self.client.get(self._get_hospitals_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        names = [h["name"] for h in data]
        self.assertIn("Hospital A", names)
        self.assertIn("Hospital B", names)

    def test_create_hospital(self):
        """Test creating a hospital."""
        response = self.client.post(
            self._get_hospitals_url(),
            {
                "name": "New Hospital",
                "address": "789 New St",
                "city": "New City",
                "phone": "1112223333",
                "email": "new@hospital.com",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Hospital")

    def test_create_department(self):
        """Test creating a department."""
        response = self.client.post(
            self._get_departments_url(),
            {
                "name": "New Department",
                "hospital": self.hospital_a.id,
                "description": "Test department",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Department")
        self.assertEqual(response.data["hospital"], self.hospital_a.id)

    def test_create_ward(self):
        """Test creating a ward."""
        response = self.client.post(
            self._get_wards_url(),
            {
                "name": "New Ward",
                "hospital": self.hospital_a.id,
                "ward_type": "ICU",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Ward")
        self.assertEqual(response.data["ward_type"], "ICU")

    def test_bed_management(self):
        """Test bed model and management."""
        dept = Department.objects.create(hospital=self.hospital_a, name="ICU")
        ward = Ward.objects.create(hospital=self.hospital_a, name="ICU Ward", ward_type="ICU")
        room = Room.objects.create(ward=ward, room_number="ICU-1", room_type="ICU")
        bed = Bed.objects.create(room=room, bed_number="1", bed_type="ICU", status="Available")
        
        self.assertEqual(bed.room, room)
        self.assertEqual(bed.status, "Available")
        
        # Occupy bed
        bed.status = "Occupied"
        bed.save()
        bed.refresh_from_db()
        self.assertEqual(bed.status, "Occupied")


class BedSetupAPITests(TestCase):
    """Adding wards, rooms and beds: only the owning hospital's Admin or Manager."""

    def setUp(self):
        self.client = APIClient()
        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)
        self.ward_a = Ward.objects.create(hospital=self.hospital_a, name="General")
        self.room_a = Room.objects.create(ward=self.ward_a, room_number="101")
        self.ward_b = Ward.objects.create(hospital=self.hospital_b, name="ICU")
        self.room_b = Room.objects.create(ward=self.ward_b, room_number="201")

        # Manager at A, only a Nurse at B.
        self.manager = self._staff("manager", [(self.hospital_a, StaffRole.HOSPITAL_MANAGER), (self.hospital_b, StaffRole.NURSE)])
        self.nurse = self._staff("nurse", [(self.hospital_a, StaffRole.NURSE)])

    def _staff(self, username, memberships):
        user = User.objects.create_user(username=username, password="testpass123")
        profile = StaffProfile.objects.create(user=user, role=memberships[0][1], employee_id=f"EMP-{username}", is_active_staff=True)
        for hospital, role in memberships:
            StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
        return user

    def _add_bed(self, user, room, hospital, **extra):
        self.client.force_authenticate(user=user)
        data = {"room": room.id, "bed_number": "B-1", "bed_type": "General", **extra}
        return self.client.post(f"/api/hospital/beds/?hospital={hospital.id}", data, format="json")

    def test_manager_adds_an_available_bed(self):
        resp = self._add_bed(self.manager, self.room_a, self.hospital_a)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        bed = Bed.objects.get(pk=resp.data["id"])
        self.assertEqual((bed.room_id, bed.bed_number, bed.status), (self.room_a.id, "B-1", "Available"))

    def test_nurse_cannot_add_a_bed(self):
        resp = self._add_bed(self.nurse, self.room_a, self.hospital_a)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Bed.objects.exists())

    def test_manager_role_elsewhere_does_not_allow_adding_beds_where_only_a_nurse(self):
        resp = self._add_bed(self.manager, self.room_b, self.hospital_a)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Bed.objects.exists())

    def test_same_bed_number_twice_in_a_room_is_refused(self):
        Bed.objects.create(room=self.room_a, bed_number="B-1")
        resp = self._add_bed(self.manager, self.room_a, self.hospital_a, bed_number=" b-1 ")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bed_number", resp.data.get("details", resp.data))
        self.assertEqual(Bed.objects.count(), 1)

    def test_new_bed_cannot_start_occupied(self):
        resp = self._add_bed(self.manager, self.room_a, self.hospital_a, status="Occupied")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Bed.objects.exists())

    def test_unknown_bed_status_is_refused(self):
        resp = self._add_bed(self.manager, self.room_a, self.hospital_a, status="Broken")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_adds_ward_and_room_and_duplicates_are_refused(self):
        self.client.force_authenticate(user=self.manager)
        url = f"?hospital={self.hospital_a.id}"
        ward = self.client.post(f"/api/hospital/wards/{url}", {"hospital": self.hospital_a.id, "name": "Maternity"}, format="json")
        self.assertEqual(ward.status_code, status.HTTP_201_CREATED, ward.data)
        dup_ward = self.client.post(f"/api/hospital/wards/{url}", {"hospital": self.hospital_a.id, "name": "maternity"}, format="json")
        self.assertEqual(dup_ward.status_code, status.HTTP_400_BAD_REQUEST)
        room = self.client.post(f"/api/hospital/rooms/{url}", {"ward": ward.data["id"], "room_number": "M1"}, format="json")
        self.assertEqual(room.status_code, status.HTTP_201_CREATED, room.data)
        dup_room = self.client.post(f"/api/hospital/rooms/{url}", {"ward": ward.data["id"], "room_number": "m1"}, format="json")
        self.assertEqual(dup_room.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rooms_can_be_listed_for_one_ward(self):
        other = Ward.objects.create(hospital=self.hospital_a, name="Surgery")
        Room.objects.create(ward=other, room_number="301")
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get(f"/api/hospital/rooms/?hospital={self.hospital_a.id}&ward={self.ward_a.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data.get("results", resp.data)
        self.assertEqual([r["room_number"] for r in rows], ["101"])
