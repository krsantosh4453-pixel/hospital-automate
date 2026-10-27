"""Queue days follow the hospital's clock (Asia/Kolkata), not the server's UTC."""

from datetime import date, datetime, time, timezone as dt_timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

# 02:30 on 28 Oct in India is still 27 Oct in UTC.
AFTER_MIDNIGHT_IN_INDIA = datetime(2026, 10, 27, 21, 0, tzinfo=dt_timezone.utc)
HOSPITAL_DAY = date(2026, 10, 28)


class HospitalDayTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Clock Hospital", is_active=True)
        user = get_user_model().objects.create_user(username="clockdesk", password="testpass123")
        profile = StaffProfile.objects.create(user=user, role=StaffRole.RECEPTIONIST, employee_id="EMP-clock", is_active_staff=True)
        StaffHospitalMembership.objects.create(staff=profile, hospital=self.hospital, role=StaffRole.RECEPTIONIST, is_active=True)
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        doctor = Doctor.objects.create(hospital=self.hospital, name="Dr Clock", specialization="General")
        patient = Patient.objects.create(name="Clock Patient", age=50, gender="Male", phone="9000000004", hospital=self.hospital)
        self.appointment = Appointment.objects.create(
            hospital=self.hospital, patient=patient, doctor=doctor, appointment_date=HOSPITAL_DAY, appointment_time=time(8, 0),
        )

    def test_token_issued_after_midnight_belongs_to_the_hospital_day(self):
        with mock.patch("django.utils.timezone.now", return_value=AFTER_MIDNIGHT_IN_INDIA):
            resp = self.client.post(f"/api/encounters/queue-tokens/issue/?hospital={self.hospital.id}", {"appointment": self.appointment.id}, format="json")
        self.assertIn(resp.status_code, (200, 201), resp.data)
        self.assertEqual(resp.data["token_date"], str(HOSPITAL_DAY))
