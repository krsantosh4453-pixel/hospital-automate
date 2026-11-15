"""Online appointment booking by a signed-in patient (synthetic data only)."""

from datetime import timedelta
from unittest.mock import patch

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

    def book(self, key=None, **data):
        body = {"doctor": self.doctor_a.id, "appointment_date": self.tomorrow, "appointment_time": "10:00", **data}
        headers = {"Idempotency-Key": key} if key else None
        return self.client_for(self.login).post(BOOK, body, format="json", headers=headers)

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

    def test_retry_with_the_same_idempotency_key_returns_the_first_booking(self):
        first = self.book(key="phone-retry-1")
        self.assertEqual(first.status_code, 201, first.content)

        retry = self.book(key="phone-retry-1")

        self.assertEqual(retry.status_code, 200, retry.content)
        self.assertEqual(retry.json()["id"], first.json()["id"])
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), 1)

    def test_idempotency_key_reused_for_a_different_booking_is_refused(self):
        self.assertEqual(self.book(key="phone-retry-2").status_code, 201)

        clash = self.book(key="phone-retry-2", appointment_time="11:00")

        self.assertEqual(clash.status_code, 409, clash.content)
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), 1)

    def test_overlong_idempotency_key_is_refused_not_truncated(self):
        resp = self.book(key="k" * 81)

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(Appointment.objects.filter(patient=self.patient).exists())

    def test_a_place_filled_by_a_writer_without_the_lock_gives_409_not_500(self):
        # Simulate a writer that skips the doctor lock filling the only place
        # between the patient's place check and insert.
        other = Patient.objects.create(name="Synthetic Other", age=40, gender="Male", phone="9000000605",
                                       hospital=self.hospital_a)
        Appointment.objects.create(hospital=self.hospital_a, patient=other, doctor=self.doctor_a,
                                   appointment_date=self.tomorrow, appointment_time="10:00", status="Scheduled")
        with patch("appointments.views.take_place", return_value=1):
            resp = self.book()

        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertFalse(Appointment.objects.filter(patient=self.patient).exists())

    def test_idempotency_keys_belong_to_one_patient(self):
        other_login = User.objects.create_user(username="booking_patient_two", password="Synthetic-Pass-123")
        other = Patient.objects.create(
            user=other_login, name="Synthetic Second", age=31, gender="Male", phone="9000000604", hospital=self.hospital_a,
        )
        PatientHospital.objects.create(patient=other, hospital=self.hospital_a, uhid="A-BOOK-2")
        self.assertEqual(self.book(key="shared-key").status_code, 201)

        theirs = self.client_for(other_login).post(
            BOOK, {"doctor": self.doctor_a.id, "appointment_date": self.tomorrow, "appointment_time": "11:00"},
            format="json", headers={"Idempotency-Key": "shared-key"},
        )

        self.assertEqual(theirs.status_code, 201, theirs.content)
        self.assertEqual(Appointment.objects.filter(patient=other).count(), 1)
