"""Blood request workflow used by the Blood bank page (synthetic data only)."""

from django.test import TestCase
from rest_framework.test import APIClient

from bloodbank.models import BloodInventory, BloodRequest
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_in_care


class BloodBankFlowTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Blood Hospital", is_active=True)
        self.user, _ = make_staff("bb_staff", self.hospital, role=StaffRole.DOCTOR)
        self.patient = Patient.objects.create(name="Synthetic Blood Patient", age=30, gender="Female", phone="9000000092", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="BB-1")
        put_in_care(self.user, self.hospital, self.patient)
        self.stock = BloodInventory.objects.create(hospital=self.hospital, blood_group="O+", component="Whole Blood", units=5)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def create(self, units):
        r = self.client.post(
            "/api/bloodbank/requests/",
            {"hospital": self.hospital.id, "patient": self.patient.id, "blood_group": "O+", "component": "Whole Blood", "units": units},
            format="json",
        )
        self.assertEqual(r.status_code, 201, getattr(r, "data", r))
        return r.data["id"]

    def test_request_approve_issue_deducts_stock(self):
        req = self.create(2)
        self.assertEqual(self.client.post(f"/api/bloodbank/requests/{req}/approve/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/bloodbank/requests/{req}/issue/").status_code, 200)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.units, 3)
        self.assertEqual(BloodRequest.objects.get(id=req).status, "Issued")

    def test_cannot_approve_more_than_stock(self):
        req = self.create(9)
        self.assertEqual(self.client.post(f"/api/bloodbank/requests/{req}/approve/").status_code, 400)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.units, 5)

    def test_reject(self):
        req = self.create(1)
        self.assertEqual(self.client.post(f"/api/bloodbank/requests/{req}/reject/").status_code, 200)
        self.assertEqual(BloodRequest.objects.get(id=req).status, "Rejected")
