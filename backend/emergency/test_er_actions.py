"""ER row actions added for requirement J3: doctor notes and the charge slip."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from doctors.models import Doctor
from emergency.models import EmergencyMedication, EmergencyNote, EmergencyOrder, EmergencyVisit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()


def staff(username, hospital, role):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=username, is_active_staff=True)
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user


class ErActionTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Hospital A", is_active=True)
        self.other_hospital = Hospital.objects.create(name="Hospital B", is_active=True)
        self.doctor_user = staff("er_doc", self.hospital, StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, hospital=self.hospital, name="Dr ER", specialization="Emergency", phone="9000000000"
        )
        patient = Patient.objects.create(name="Asha", age=30, gender="Female", phone="9999999999", hospital=self.hospital)
        PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid="U1", is_active=True)
        self.visit = EmergencyVisit.objects.create(
            patient=patient, hospital=self.hospital, visit_number="ER-1", attending_doctor=self.doctor,
            status="Under Consultation",
        )
        self.client = APIClient()

    def url(self, action):
        return f"/api/emergency/emergency-visits/{self.visit.pk}/{action}/"

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return {"HTTP_X_HOSPITAL_ID": str(self.hospital.pk)}

    def test_doctor_adds_a_note_that_appears_on_the_visit(self):
        header = self.as_user(self.doctor_user)

        created = self.client.post(self.url("add_note"), {"note": "Chest pain settled after GTN."}, format="json", **header)
        visit = self.client.get(f"/api/emergency/emergency-visits/{self.visit.pk}/", **header)

        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(EmergencyNote.objects.get().written_by, self.doctor_user)
        self.assertEqual([n["note"] for n in visit.data["notes"]], ["Chest pain settled after GTN."])

    def test_empty_note_is_refused(self):
        response = self.client.post(self.url("add_note"), {"note": "  "}, format="json", **self.as_user(self.doctor_user))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_cannot_write_notes(self):
        manager = staff("mgr", self.hospital, StaffRole.HOSPITAL_MANAGER)

        response = self.client.post(self.url("add_note"), {"note": "x"}, format="json", **self.as_user(manager))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_charge_slip_lists_orders_and_medicines_in_time_order(self):
        EmergencyOrder.objects.create(visit=self.visit, order_type="Lab", description="CBC")
        EmergencyMedication.objects.create(visit=self.visit, name="Paracetamol", dose="500 mg", route="Oral", frequency="Once", administered=True)

        response = self.client.get(self.url("charge_slip"), **self.as_user(self.doctor_user))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [(line["description"], line["status"]) for line in response.data["lines"]],
            [("CBC", "Ordered"), ("Paracetamol 500 mg Oral", "Given")],
        )
        self.assertEqual(response.data["visit_number"], "ER-1")

    def test_other_hospital_cannot_read_the_charge_slip(self):
        outsider = staff("doc_b", self.other_hospital, StaffRole.DOCTOR)
        self.client.force_authenticate(user=outsider)

        response = self.client.get(self.url("charge_slip"), HTTP_X_HOSPITAL_ID=str(self.other_hospital.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
