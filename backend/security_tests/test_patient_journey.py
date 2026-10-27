"""
One OPD patient from booking to a paid bill, through the real API and each
role's own account: Receptionist books and issues the token, Doctor sees the
patient and prescribes, Pharmacist dispenses, Billing Staff bills and takes
payment. Every step must leave the records in a consistent state.
"""

from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from billing.models import Invoice
from clinical.models import Prescription
from doctors.models import Doctor
from encounters.models import QueueToken
from hospital.models import Hospital
from patients.models import Patient
from pharmacy.models import Medicine
from users.models import StaffHospitalMembership, StaffProfile, StaffRole


class PatientJourneyTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Journey Hospital", is_active=True)
        self.scope = f"?hospital={self.hospital.id}"
        self.desk = self._staff("desk", StaffRole.RECEPTIONIST)
        self.doctor_user = self._staff("doc", StaffRole.DOCTOR)
        self.pharmacist = self._staff("pharma", StaffRole.PHARMACIST)
        self.biller = self._staff("bill", StaffRole.BILLING_STAFF)
        self.doctor = Doctor.objects.create(hospital=self.hospital, user=self.doctor_user, name="Dr Journey", specialization="General")
        self.patient = Patient.objects.create(name="Journey Patient", age=35, gender="Male", phone="9000000003", hospital=self.hospital)
        self.medicine = Medicine.objects.create(hospital=self.hospital, name="Paracetamol 500", quantity=100, price=Decimal("2.50"))

    def _staff(self, username, role):
        user = get_user_model().objects.create_user(username=username, password="testpass123")
        profile = StaffProfile.objects.create(user=user, role=role, employee_id=f"EMP-{username}", is_active_staff=True)
        StaffHospitalMembership.objects.create(staff=profile, hospital=self.hospital, role=role, is_active=True)
        return user

    def _as(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _ok(self, resp, *codes):
        self.assertIn(resp.status_code, codes or (200, 201), getattr(resp, "data", resp))
        return resp.data

    def test_opd_patient_from_booking_to_paid_bill(self):
        desk, doctor, pharmacy, billing = (self._as(u) for u in (self.desk, self.doctor_user, self.pharmacist, self.biller))

        # 1. Front desk books the appointment.
        appt = self._ok(desk.post(f"/api/appointments/{self.scope}", {
            "hospital": self.hospital.id, "patient": self.patient.id, "doctor": self.doctor.id,
            "appointment_date": str(date.today()), "appointment_time": str(time(11, 0)), "reason": "Fever",
        }, format="json"), 201)
        self.assertEqual(appt["status"], "Scheduled")

        # 2. Front desk issues the queue token; the appointment is checked in.
        token = self._ok(desk.post(f"/api/encounters/queue-tokens/issue/{self.scope}", {"appointment": appt["id"]}, format="json"), 200, 201)
        self.assertEqual(Appointment.objects.get(pk=appt["id"]).status, "Checked In")

        # 3. The doctor calls the patient in and starts the consultation.
        self._ok(doctor.post(f"/api/encounters/queue-tokens/call-next/{self.scope}"), 200)
        self._ok(doctor.post(f"/api/encounters/queue-tokens/{token['id']}/start-consultation/{self.scope}"), 200)
        self.assertEqual(Appointment.objects.get(pk=appt["id"]).status, "In Consultation")

        # 4. The doctor prescribes.
        rx = self._ok(doctor.post(f"/api/clinical/prescriptions/{self.scope}", {
            "hospital": self.hospital.id, "patient": self.patient.id, "doctor": self.doctor.id, "visit": token["visit"],
            "items": [{"name": "Paracetamol 500", "dosage": "500 mg", "frequency": "1-0-1", "duration": "5 days", "quantity": 10}],
        }, format="json"), 201)

        # 5. The doctor completes the consultation.
        self._ok(doctor.post(f"/api/encounters/queue-tokens/{token['id']}/complete/{self.scope}"), 200)
        self.assertEqual(QueueToken.objects.get(pk=token["id"]).status, "Completed")
        self.assertEqual(Appointment.objects.get(pk=appt["id"]).status, "Completed")

        # 6. The pharmacist dispenses against the prescription; stock goes down
        #    and the prescription is marked dispensed.
        sale = self._ok(pharmacy.post(f"/api/pharmacy-sales/{self.scope}", {
            "medicine": self.medicine.id, "patient_name": self.patient.name, "quantity": 10, "prescription": rx["id"],
        }, format="json"), 201)
        self.assertEqual(Decimal(str(sale["total"])), Decimal("25.00"))
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.quantity, 90)
        dispensed = Prescription.objects.get(pk=rx["id"])
        self.assertEqual(dispensed.status, "Dispensed")
        self.assertIsNotNone(dispensed.dispensed_at)

        # 7. Billing raises the invoice and takes full payment.
        invoice = self._ok(billing.post(f"/api/billing/invoices/{self.scope}", {
            "hospital": self.hospital.id, "patient": self.patient.id,
            "items_data": [
                {"description": "Consultation", "quantity": 1, "unit_price": "300.00", "tax_rate": "0"},
                {"description": "Paracetamol 500 x10", "quantity": 1, "unit_price": "25.00", "tax_rate": "0"},
            ],
        }, format="json"), 201)
        self.assertEqual(Decimal(str(invoice["total"])), Decimal("325.00"))
        self._ok(billing.post(f"/api/billing/payments/{self.scope}", {
            "invoice": invoice["id"], "amount": "325.00", "payment_method": "Cash",
        }, format="json"), 201)
        paid = Invoice.objects.get(pk=invoice["id"])
        self.assertEqual(paid.status, "Paid")
