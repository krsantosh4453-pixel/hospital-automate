"""Setting up a hospital: who may add one, and a ward with its beds in one step."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from hospital.models import Bed, Hospital, Room, Ward
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()


def make_staff(username, role, memberships=()):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=f"EMP-{username}", is_active_staff=True)
    for hospital, member_role in memberships:
        StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=member_role, is_active=True)
    return user


class AddHospitalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.existing = Hospital.objects.create(name="Existing", is_active=True)

    def _add(self, user, name="City Care"):
        self.client.force_authenticate(user=user)
        return self.client.post("/api/hospital/hospitals/", {"name": name, "code": "cc1", "phone": "9000000000"}, format="json")

    def test_new_admin_account_adds_hospital_and_becomes_its_admin(self):
        owner = make_staff("owner", StaffRole.ADMIN)
        resp = self._add(owner)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        membership = StaffHospitalMembership.objects.get(staff__user=owner, hospital_id=resp.data["id"])
        self.assertEqual((membership.role, membership.is_active), (StaffRole.ADMIN, True))
        self.assertEqual(resp.data["code"], "CC1")

    def test_admin_of_a_hospital_adds_another(self):
        admin = make_staff("admin", StaffRole.ADMIN, [(self.existing, StaffRole.ADMIN)])
        self.assertEqual(self._add(admin).status_code, status.HTTP_201_CREATED)
        self.assertEqual(StaffHospitalMembership.objects.filter(staff__user=admin).count(), 2)

    def test_manager_or_doctor_cannot_add_a_hospital(self):
        manager = make_staff("manager", StaffRole.HOSPITAL_MANAGER, [(self.existing, StaffRole.HOSPITAL_MANAGER)])
        doctor = make_staff("doctor", StaffRole.DOCTOR, [(self.existing, StaffRole.DOCTOR)])
        for user in (manager, doctor):
            self.assertEqual(self._add(user).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Hospital.objects.count(), 1)

    def test_demoted_admin_with_old_profile_role_cannot_add(self):
        # Profile role is a display default; only the membership grants Admin.
        former = make_staff("former", StaffRole.ADMIN, [(self.existing, StaffRole.RECEPTIONIST)])
        self.assertEqual(self._add(former).status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_admin_registration_cannot_add(self):
        pending = make_staff("pending", StaffRole.ADMIN)
        pending.staff_profile.is_active_staff = False
        pending.staff_profile.save()
        self.assertEqual(self._add(pending).status_code, status.HTTP_403_FORBIDDEN)


class WardWithBedsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="A", is_active=True)
        self.other = Hospital.objects.create(name="B", is_active=True)
        self.admin = make_staff("admin", StaffRole.ADMIN, [(self.hospital, StaffRole.ADMIN), (self.other, StaffRole.NURSE)])
        self.client.force_authenticate(user=self.admin)

    def _post(self, hospital, data):
        return self.client.post(
            f"/api/hospital/wards/with-beds/?hospital={hospital.id}", {"hospital": hospital.id, **data}, format="json"
        )

    def test_creates_ward_rooms_and_numbered_beds(self):
        resp = self._post(self.hospital, {
            "name": "General", "ward_type": "General",
            "rooms": [{"room_number": "101", "beds": 3, "bed_type": "General"}, {"room_number": "102", "beds": 2}],
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual((resp.data["room_count"], resp.data["bed_count"]), (2, 5))
        beds = Bed.objects.filter(room__ward_id=resp.data["id"]).order_by("bed_number")
        self.assertEqual([b.bed_number for b in beds], ["101-1", "101-2", "101-3", "102-1", "102-2"])
        self.assertTrue(all(b.status == "Available" for b in beds))

    def test_duplicate_ward_or_room_creates_nothing(self):
        Ward.objects.create(hospital=self.hospital, name="General")
        self.assertEqual(self._post(self.hospital, {"name": "general", "rooms": [{"room_number": "1", "beds": 1}]}).status_code, 400)
        self.assertEqual(self._post(self.hospital, {"name": "ICU", "rooms": [{"room_number": "1", "beds": 1}, {"room_number": "1", "beds": 1}]}).status_code, 400)
        self.assertEqual(Room.objects.count(), 0)

    def test_bed_count_limits(self):
        for beds in (0, 51):
            resp = self._post(self.hospital, {"name": f"W{beds}", "rooms": [{"room_number": "1", "beds": beds}]})
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Ward.objects.exists())

    def test_nurse_cannot_set_up_wards(self):
        resp = self._post(self.other, {"name": "ICU", "rooms": [{"room_number": "1", "beds": 1}]})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Ward.objects.exists())

    def test_cannot_target_another_hospital_through_the_body(self):
        resp = self.client.post(
            f"/api/hospital/wards/with-beds/?hospital={self.hospital.id}",
            {"hospital": self.other.id, "name": "ICU", "rooms": [{"room_number": "1", "beds": 1}]}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Ward.objects.exists())
