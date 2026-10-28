"""Sample barcode scan (F6)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from hospital.models import Hospital
from laboratory.models import LabTest, SampleCollection
from patients.models import Patient, PatientHospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
URL = "/api/laboratory/by_sample/"


def staff(username, hospital, role):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=username, is_active_staff=True)
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user


def sample(hospital, sample_id, patient_phone):
    patient = Patient.objects.create(name="P", age=30, gender="Female", phone=patient_phone, hospital=hospital)
    PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=sample_id, is_active=True)
    test = LabTest.objects.create(hospital=hospital, patient=patient, name="CBC", status="Collected")
    SampleCollection.objects.create(lab_test=test, sample_type="Blood", container_type="EDTA", sample_id=sample_id)
    return test


class SampleScanTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="A", is_active=True)
        self.other = Hospital.objects.create(name="B", is_active=True)
        self.test = sample(self.hospital, "LAB20261028-1-000001", "9000000001")
        self.foreign = sample(self.other, "LAB20261028-2-000002", "9000000002")
        self.client = APIClient()

    def scan(self, user, code, hospital=None):
        self.client.force_authenticate(user=user)
        return self.client.get(URL, {"sample_id": code}, HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).pk))

    def test_scan_finds_the_order_case_insensitively(self):
        response = self.scan(staff("lab", self.hospital, StaffRole.LAB_STAFF), "lab20261028-1-000001")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual((response.data["id"], response.data["status"]), (self.test.pk, "Collected"))

    def test_another_hospitals_sample_is_not_found(self):
        response = self.scan(staff("lab", self.hospital, StaffRole.LAB_STAFF), "LAB20261028-2-000002")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_scan_is_refused(self):
        response = self.scan(staff("lab", self.hospital, StaffRole.LAB_STAFF), "  ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_lab_staff_and_nurses_scan(self):
        response = self.scan(staff("rec", self.hospital, StaffRole.RECEPTIONIST), "LAB20261028-1-000001")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
