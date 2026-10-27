"""Online appointment booking by a signed-in patient (synthetic data only)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from appointments.views import BOOKING_WINDOW_DAYS, MAX_UPCOMING_BOOKINGS, _hospital_now
from audit.models import AuditLog
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

User = get_user_model()
OPTIONS = "/api/appointments/booking-options/"
BOOK = "/api/appointments/book/"


class PatientBookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital_a = Hospital.objects.create(name="Synthetic A", is_active=True)
        cls.hospital_b = Hospital.objects.create(name="Synthetic B", is_active=True)
        cls.doctor_a = Doctor.objects.create(hospital=cls.hospital_a, name="Dr A", specialization="General", phone="9000000601")
        cls.doctor_b = Doctor.objects.create(hospital=cls.hospital_b, name="Dr B", specialization="General", phone="9000000602")
        cls.login = User.objects.create_user(username="booking_patient", password="Synthetic-Pass-123")
        cls.patient = Patient.objects.create(
            user=cls.login, name="Synthetic Booker", age=30, gender="Female", phone="9000000603", hospital=cls.hospital_a,
        )
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital_a, uhid="A-BOOK")
        cls.tomorrow = (_hospital_now().date() + timedelta(days=1)).isoformat()

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        if user is not None:
            client.force_authenticate(user)
        return client

    def book(self, **data):
        body = {"doctor": self.doctor_a.id, "appointment_date": self.tomorrow, "appointment_time": "10:00", **data}
        return self.client_for(self.login).post(BOOK, body, format="json")

    def test_options_show_only_the_patients_hospitals_and_their_doctors(self):
        client = self.client_for(self.login)
        body = client.get(OPTIONS).json()
        self.assertEqual([h["id"] for h in body["hospitals"]], [self.hospital_a.id])
        doctors = client.get(OPTIONS, {"hospital": self.hospital_a.id}).json()["doctors"]
        self.assertEqual([d["id"] for d in doctors], [self.doctor_a.id])
        self.assertEqual(client.get(OPTIONS, {"hospital": self.hospital_b.id}).status_code, 403)

    def test_slots_mark_taken_times(self):
        self.assertEqual(self.book().status_code, 201)
        slots = self.client_for(self.login).get(
            OPTIONS, {"hospital": self.hospital_a.id, "doctor": self.doctor_a.id, "date": self.tomorrow}
        ).json()["slots"]
        taken = {s["time"]: s["available"] for s in slots}
        self.assertFalse(taken["10:00"])
        self.assertTrue(taken["10:15"])

    def test_patient_books_for_themselves(self):
        resp = self.book(reason="Fever", patient=999)
        self.assertEqual(resp.status_code, 201, resp.content)
        appt = Appointment.objects.get(pk=resp.json()["id"])
        self.assertEqual(appt.patient, self.patient)
        self.assertEqual(appt.hospital, self.hospital_a)
        self.assertEqual(appt.status, "Scheduled")
        self.assertTrue(AuditLog.objects.filter(action="appointments.appointment.self_booked").exists())

    def test_same_slot_cannot_be_booked_twice(self):
        self.assertEqual(self.book().status_code, 201)
        self.assertEqual(self.book().status_code, 409)

    def test_invalid_dates_and_times_are_refused(self):
        yesterday = (_hospital_now().date() - timedelta(days=1)).isoformat()
        too_far = (_hospital_now().date() + timedelta(days=BOOKING_WINDOW_DAYS + 1)).isoformat()
        self.assertEqual(self.book(appointment_date=yesterday).status_code, 400)
        self.assertEqual(self.book(appointment_date=too_far).status_code, 400)
        self.assertEqual(self.book(appointment_time="10:07").status_code, 400)
        self.assertEqual(self.book(appointment_time="20:00").status_code, 400)

    def test_doctor_of_another_hospital_is_refused(self):
        self.assertEqual(self.book(doctor=self.doctor_b.id).status_code, 400)
        self.assertFalse(Appointment.objects.filter(doctor=self.doctor_b).exists())

    def test_upcoming_bookings_are_limited(self):
        for i in range(MAX_UPCOMING_BOOKINGS):
            self.assertEqual(self.book(appointment_time=f"1{i}:00").status_code, 201)
        self.assertEqual(self.book(appointment_time="15:00").status_code, 400)

    def test_staff_and_anonymous_cannot_use_patient_booking(self):
        staff, _ = make_staff("booking_reception", self.hospital_a, role=StaffRole.RECEPTIONIST)
        self.assertEqual(self.client_for(staff).post(BOOK, {}, format="json").status_code, 403)
        self.assertEqual(self.client_for(None).post(BOOK, {}, format="json").status_code, 401)
