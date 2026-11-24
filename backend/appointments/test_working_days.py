"""
Prompt 4 (E2E audit BUG-003): a doctor who works "Mon-Sat" could be booked on
a Sunday. Working days come from the doctor's own ``availability`` text; a
text naming no days keeps today's unrestricted behaviour. Synthetic data only.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from appointments.availability import parse_working_days
from appointments.models import Appointment
from appointments.views import _hospital_now
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

User = get_user_model()
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


class ParseWorkingDaysTests(SimpleTestCase):
    def test_ranges_lists_and_words(self):
        cases = {
            "Mon-Sat 09:00-17:00": {MON, TUE, WED, THU, FRI, SAT},
            "Mon to Fri, 10am-2pm": {MON, TUE, WED, THU, FRI},
            "Mon, Wed, Fri": {MON, WED, FRI},
            "Tuesday & Thursday": {TUE, THU},
            "Fri-Mon": {FRI, SAT, SUN, MON},
            "Weekdays": {MON, TUE, WED, THU, FRI},
            "Weekends only": {SAT, SUN},
            "Daily 8-8": set(range(7)),
            "All days": set(range(7)),
            "sat sun": {SAT, SUN},
        }
        for text, days in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_working_days(text), days)

    def test_text_without_days_sets_no_rule(self):
        for text in ("", None, "09:00-17:00", "On call", "Available"):
            with self.subTest(text=text):
                self.assertIsNone(parse_working_days(text))


class WorkingDayBookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Weekdays", is_active=True)
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, name="Dr Weekday", specialization="General",
                                           phone="9000072001", availability="Mon-Sat 09:00-17:00")
        cls.open_doctor = Doctor.objects.create(hospital=cls.hospital, name="Dr Any Day", specialization="General",
                                                phone="9000072002", availability="")
        cls.reception, _ = make_staff("wd_reception", cls.hospital, role=StaffRole.RECEPTIONIST)
        login = User.objects.create_user(username="wd_patient")
        cls.patient = Patient.objects.create(user=login, name="Synthetic Weekday Patient", age=30,
                                             gender="Female", phone="9000072101", hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="WD-1")
        today = _hospital_now().date()
        cls.sunday = next(today + timedelta(days=n) for n in range(1, 9) if (today + timedelta(days=n)).weekday() == SUN)
        cls.monday = cls.sunday + timedelta(days=1)

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def self_book(self, doctor, day):
        return self.client_for(self.patient.user).post("/api/appointments/book/", {
            "doctor": doctor.id, "appointment_date": day.isoformat(), "appointment_time": "10:00"}, format="json")

    def test_1_unavailable_day_is_refused_with_a_clear_message(self):
        response = self.self_book(self.doctor, self.sunday)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("does not see patients on Sunday", str(response.content))
        self.assertFalse(Appointment.objects.exists())

    def test_2_a_working_day_is_still_bookable(self):
        self.assertEqual(self.self_book(self.doctor, self.monday).status_code, 201)

    def test_a_doctor_with_no_days_written_keeps_every_day(self):
        self.assertEqual(self.self_book(self.open_doctor, self.sunday).status_code, 201)

    def test_3_booking_options_offer_no_slots_on_a_day_off_and_say_why(self):
        data = self.client_for(self.patient.user).get(
            f"/api/appointments/booking-options/?hospital={self.hospital.id}&doctor={self.doctor.id}"
            f"&date={self.sunday.isoformat()}").json()

        self.assertEqual(data["slots"], [])
        self.assertIn("Sunday", data["unavailable_reason"])
        doctor = next(d for d in data["doctors"] if d["id"] == self.doctor.id)
        self.assertEqual(doctor["working_days"], [MON, TUE, WED, THU, FRI, SAT])
        anyday = next(d for d in data["doctors"] if d["id"] == self.open_doctor.id)
        self.assertIsNone(anyday["working_days"])

    def test_staff_bookings_and_reschedules_respect_the_days_too(self):
        desk = self.client_for(self.reception)
        refused = desk.post("/api/appointments/", {
            "hospital": self.hospital.id, "patient": self.patient.id, "doctor": self.doctor.id,
            "appointment_date": self.sunday.isoformat(), "appointment_time": "10:00", "status": "Scheduled"},
            format="json")
        self.assertEqual(refused.status_code, 400, refused.content)

        booked = desk.post("/api/appointments/", {
            "hospital": self.hospital.id, "patient": self.patient.id, "doctor": self.doctor.id,
            "appointment_date": self.monday.isoformat(), "appointment_time": "10:00", "status": "Scheduled"},
            format="json")
        self.assertEqual(booked.status_code, 201, booked.content)
        moved = desk.post(f"/api/appointments/{booked.json()['id']}/reschedule/",
                          {"appointment_date": self.sunday.isoformat()}, format="json")
        self.assertEqual(moved.status_code, 400, moved.content)
        self.assertEqual(Appointment.objects.get(pk=booked.json()["id"]).appointment_date, self.monday)
