"""
A prescription records who prescribed it, and "Dispensed" means medicine was
really handed over. Found by the 2026-11-05 browser workflow test: a doctor's
PATCH could mark a prescription Dispensed with no sale or stock movement, and
a doctor could write a prescription in another doctor's name.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import Prescription, PrescriptionItem
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

URL = "/api/clinical/prescriptions/"


class PrescriptionIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Rx Hospital", is_active=True)
        cls.doctor_user, _ = make_staff("rx_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.other_user, _ = make_staff("rx_other_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.admin_user, _ = make_staff("rx_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.doctor = Doctor.objects.create(user=cls.doctor_user, hospital=cls.hospital, name="Dr Synthetic A",
                                           specialization="General", phone="9000000801")
        cls.other_doctor = Doctor.objects.create(user=cls.other_user, hospital=cls.hospital, name="Dr Synthetic B",
                                                 specialization="General", phone="9000000802")
        cls.patient = Patient.objects.create(name="Synthetic Rx Patient", age=40, gender="Male",
                                             phone="9000000803", hospital=cls.hospital)
        put_in_care(cls.doctor_user, cls.hospital, cls.patient)

    def api(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def body(self, **extra):
        return {"hospital": self.hospital.id, "patient": self.patient.id,
                "items": [{"name": "Paracetamol 500mg", "quantity": 3}], **extra}

    def confirmed_prescription(self):
        prescription = Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor)
        PrescriptionItem.objects.create(prescription=prescription, name="Paracetamol 500mg", quantity=3)
        return prescription

    def test_doctor_cannot_mark_a_prescription_dispensed(self):
        prescription = self.confirmed_prescription()
        for status in ("Dispensed", "Partially Dispensed"):
            with self.subTest(status=status):
                response = self.api(self.doctor_user).patch(f"{URL}{prescription.pk}/", {"status": status}, format="json")
                self.assertEqual(response.status_code, 400, response.content)
                prescription.refresh_from_db()
                self.assertEqual(prescription.status, "Confirmed")
                self.assertIsNone(prescription.dispensed_at)

    def test_a_new_prescription_cannot_start_dispensed(self):
        response = self.api(self.doctor_user).post(URL, self.body(status="Dispensed"), format="json")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Prescription.objects.exists())

    def test_doctor_can_still_cancel(self):
        prescription = self.confirmed_prescription()
        response = self.api(self.doctor_user).patch(f"{URL}{prescription.pk}/", {"status": "Cancelled"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, "Cancelled")

    def test_doctor_cannot_prescribe_in_another_doctors_name(self):
        response = self.api(self.doctor_user).post(URL, self.body(doctor=self.other_doctor.id), format="json")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("doctor", response.json()["details"])
        self.assertFalse(Prescription.objects.exists())

    def test_doctor_cannot_move_a_prescription_to_another_doctor(self):
        prescription = self.confirmed_prescription()
        response = self.api(self.doctor_user).patch(f"{URL}{prescription.pk}/", {"doctor": self.other_doctor.id},
                                                    format="json")
        self.assertEqual(response.status_code, 400, response.content)
        prescription.refresh_from_db()
        self.assertEqual(prescription.doctor, self.doctor)

    def test_doctor_without_a_named_prescriber_signs_it_themself(self):
        response = self.api(self.doctor_user).post(URL, self.body(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Prescription.objects.get().doctor, self.doctor)

    def test_admin_may_record_a_prescription_for_any_doctor_of_the_hospital(self):
        response = self.api(self.admin_user).post(URL, self.body(doctor=self.other_doctor.id), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Prescription.objects.get().doctor, self.other_doctor)
