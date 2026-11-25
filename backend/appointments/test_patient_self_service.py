"""
Prompt 5 (MF-003 / INT-003): a patient cancels or moves their own booking.
The booking rules stay the server's: the same window, working days, slot
list, capacity and clash checks as booking. Synthetic data only.
"""
import unittest
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from appointments.views import BOOKING_WINDOW_DAYS, _hospital_now
from audit.models import AuditLog
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital

User = get_user_model()
SUN = 6


def next_weekday(start, weekday):
    return next(start + timedelta(days=n) for n in range(1, 9) if (start + timedelta(days=n)).weekday() == weekday)


class PatientSelfServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Self Service", is_active=True)
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, name="Dr Synthetic Slots", specialization="General",
                                           phone="9000073001", availability="Mon-Sat 09:00-17:00", slot_capacity=1)
        cls.patient = cls._patient("ss_patient", "9000073101")
        cls.other = cls._patient("ss_other", "9000073102")
        today = _hospital_now().date()
        cls.monday = next_weekday(today, 0)
        cls.tuesday = cls.monday + timedelta(days=1)
        cls.sunday = next_weekday(today, SUN)

    @classmethod
    def _patient(cls, username, phone):
        login = User.objects.create_user(username=username)
        patient = Patient.objects.create(user=login, name=f"Synthetic {username}", age=30, gender="Female",
                                         phone=phone, hospital=cls.hospital)
        PatientHospital.objects.create(patient=patient, hospital=cls.hospital, uhid=f"SS-{username}")
        return patient

    def client_for(self, patient):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(patient.user)
        return client

    def book(self, patient, day, at="10:00"):
        response = self.client_for(patient).post("/api/appointments/book/", {
            "doctor": self.doctor.id, "appointment_date": day.isoformat(), "appointment_time": at}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return Appointment.objects.get(pk=response.data["id"])

    def cancel(self, patient, appointment, reason="Feeling better"):
        return self.client_for(patient).post(f"/api/appointments/{appointment.pk}/self-cancel/",
                                             {"reason": reason}, format="json")

    def move(self, patient, appointment, day, at="11:00"):
        return self.client_for(patient).post(f"/api/appointments/{appointment.pk}/self-reschedule/", {
            "appointment_date": day.isoformat(), "appointment_time": at}, format="json")

    # --- cancel ---------------------------------------------------------------

    def test_a_patient_cancels_their_booking_and_the_slot_is_free_again(self):
        mine = self.book(self.patient, self.monday)

        response = self.cancel(self.patient, mine)

        self.assertEqual(response.status_code, 200, response.content)
        mine.refresh_from_db()
        self.assertEqual(mine.status, "Cancelled")
        entry = AuditLog.objects.get(action="appointments.appointment.self_cancelled", object_id=str(mine.pk))
        self.assertIn("Feeling better", entry.details)
        self.book(self.other, self.monday)  # capacity 1: the place came back

    def test_nobody_cancels_someone_elses_booking(self):
        theirs = self.book(self.other, self.monday)
        self.assertEqual(self.cancel(self.patient, theirs).status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, "Scheduled")

    def test_only_a_scheduled_future_booking_can_be_cancelled(self):
        for hour, status in enumerate(("Checked In", "In Consultation", "Completed", "Cancelled", "No Show"), 12):
            booking = Appointment.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                                 appointment_date=self.tuesday, appointment_time=time(hour, 0),
                                                 status=status)
            with self.subTest(status=status):
                self.assertEqual(self.cancel(self.patient, booking).status_code, 400)
                booking.refresh_from_db()
                self.assertEqual(booking.status, status)
        past = Appointment.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                          appointment_date=_hospital_now().date() - timedelta(days=1),
                                          appointment_time=time(10, 0), status="Scheduled")
        self.assertEqual(self.cancel(self.patient, past).status_code, 400)

    def test_the_staff_cancel_endpoint_stays_staff_only(self):
        mine = self.book(self.patient, self.monday)
        response = self.client_for(self.patient).post(f"/api/appointments/{mine.pk}/cancel/")
        self.assertEqual(response.status_code, 403)

    # --- reschedule -----------------------------------------------------------

    def test_a_patient_moves_their_booking_to_a_free_slot(self):
        mine = self.book(self.patient, self.monday)

        response = self.move(self.patient, mine, self.tuesday, "11:30")

        self.assertEqual(response.status_code, 200, response.content)
        mine.refresh_from_db()
        self.assertEqual((mine.appointment_date, mine.appointment_time, mine.status),
                         (self.tuesday, time(11, 30), "Scheduled"))
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), 1)
        entry = AuditLog.objects.get(action="appointments.appointment.self_rescheduled", object_id=str(mine.pk))
        self.assertIn(self.monday.isoformat(), entry.details)
        self.book(self.other, self.monday)  # the old place is free

    def test_a_refused_move_leaves_the_booking_exactly_as_it_was(self):
        mine = self.book(self.patient, self.monday)
        self.book(self.other, self.tuesday, "11:00")  # capacity 1: that slot is full
        now = _hospital_now().date()
        cases = {
            "day off": (self.sunday, "10:00", 400),
            "full slot": (self.tuesday, "11:00", 409),
            "past day": (now - timedelta(days=1), "10:00", 400),
            "beyond the window": (now + timedelta(days=BOOKING_WINDOW_DAYS + 7), "10:00", 400),
            "not a slot": (self.tuesday, "10:07", 400),
        }
        for label, (day, at, expected) in cases.items():
            with self.subTest(label):
                self.assertEqual(self.move(self.patient, mine, day, at).status_code, expected)
                mine.refresh_from_db()
                self.assertEqual((mine.appointment_date, mine.appointment_time, mine.status),
                                 (self.monday, time(10, 0), "Scheduled"))
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), 1)

    def test_nobody_moves_someone_elses_or_a_finished_booking(self):
        theirs = self.book(self.other, self.monday)
        done = Appointment.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                          appointment_date=self.tuesday, appointment_time=time(15, 0),
                                          status="Completed")
        self.assertEqual(self.move(self.patient, theirs, self.tuesday).status_code, 404)
        self.assertEqual(self.move(self.patient, done, self.tuesday, "16:00").status_code, 400)

    def test_staff_cannot_use_the_patient_endpoints(self):
        from security_tests.test_tenant_isolation import make_staff
        from users.models import StaffRole

        mine = self.book(self.patient, self.monday)
        reception, _ = make_staff("ss_desk", self.hospital, role=StaffRole.RECEPTIONIST)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(reception)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        self.assertEqual(client.post(f"/api/appointments/{mine.pk}/self-cancel/", {}, format="json").status_code, 403)



@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ParallelRescheduleTests(TransactionTestCase):
    """Prompt 5: patients moving into the last place at once; the slot never overfills."""

    def test_parallel_moves_into_one_place_seat_one_patient(self):
        from security_tests.test_concurrency import run_together

        hospital = Hospital.objects.create(name="Synthetic Move Race", is_active=True)
        doctor = Doctor.objects.create(hospital=hospital, name="Dr Synthetic Race", specialization="General",
                                       phone="9000073501", availability="Mon-Sat", slot_capacity=1)
        today = _hospital_now().date()
        monday, tuesday = next_weekday(today, 0), next_weekday(today, 0) + timedelta(days=1)
        patients, bookings = [], []
        for n in range(4):
            login = User.objects.create_user(username=f"race_move_{n}")
            patient = Patient.objects.create(user=login, name=f"Synthetic Race {n}", age=30, gender="Male",
                                             phone=f"90000736{n:02d}", hospital=hospital)
            PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=f"RM-{n}")
            patients.append(patient)
            bookings.append(Appointment.objects.create(
                hospital=hospital, patient=patient, doctor=doctor, appointment_date=monday,
                appointment_time=time(9 + n, 0), status="Scheduled"))

        def move(index):
            client = APIClient(raise_request_exception=False)
            client.force_authenticate(patients[index].user)
            return client.post(f"/api/appointments/{bookings[index].pk}/self-reschedule/",
                               {"appointment_date": tuesday.isoformat(), "appointment_time": "16:00"},
                               format="json").status_code

        codes = run_together(move, count=4)

        self.assertEqual(sorted(codes), [200, 409, 409, 409], codes)
        self.assertEqual(Appointment.objects.filter(doctor=doctor, appointment_date=tuesday,
                                                    appointment_time=time(16, 0)).count(), 1)
        self.assertEqual(Appointment.objects.filter(doctor=doctor, appointment_date=monday).count(), 3)
