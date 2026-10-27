"""Appointment status: one fixed list, kept in step with the queue token by the server."""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from appointments.models import Appointment
from doctors.models import Doctor
from encounters.models import QueueToken
from hospital.models import Hospital
from patients.models import Patient
from users.models import StaffHospitalMembership, StaffProfile, StaffRole


class AppointmentStatusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="Status Hospital", is_active=True)
        user = get_user_model().objects.create_user(username="desk", password="testpass123")
        profile = StaffProfile.objects.create(user=user, role=StaffRole.ADMIN, employee_id="EMP-desk", is_active_staff=True)
        StaffHospitalMembership.objects.create(staff=profile, hospital=self.hospital, role=StaffRole.ADMIN, is_active=True)
        self.client.force_authenticate(user=user)
        self.doctor = Doctor.objects.create(hospital=self.hospital, name="Dr Status", specialization="General")
        self.patient = Patient.objects.create(name="Status Patient", age=30, gender="Female", phone="9000000002", hospital=self.hospital)
        self.appointment = Appointment.objects.create(
            hospital=self.hospital, patient=self.patient, doctor=self.doctor,
            appointment_date=date.today(), appointment_time=time(10, 0),
        )
        self.scope = f"?hospital={self.hospital.id}"

    def _status(self):
        self.appointment.refresh_from_db()
        return self.appointment.status

    def _token_action(self, token, action):
        resp = self.client.post(f"/api/encounters/queue-tokens/{token.id}/{action}/{self.scope}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def _issue(self):
        resp = self.client.post(f"/api/encounters/queue-tokens/issue/{self.scope}", {"appointment": self.appointment.id}, format="json")
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), resp.data)
        return QueueToken.objects.get(pk=resp.data["id"])

    def test_new_appointment_is_scheduled(self):
        self.assertEqual(self.appointment.status, Appointment.Status.SCHEDULED)

    def test_unknown_status_is_refused(self):
        resp = self.client.patch(f"/api/appointments/{self.appointment.id}/{self.scope}", {"status": "Confirmed"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._status(), "Scheduled")

    def test_token_flow_moves_the_appointment_along(self):
        token = self._issue()
        self.assertEqual(self._status(), "Checked In")
        self._token_action(token, "call")
        self.assertEqual(self._status(), "Checked In")
        self._token_action(token, "start-consultation")
        self.assertEqual(self._status(), "In Consultation")
        self._token_action(token, "complete")
        self.assertEqual(self._status(), "Completed")

    def test_no_show_token_marks_the_appointment(self):
        token = self._issue()
        self._token_action(token, "no-show")
        self.assertEqual(self._status(), "No Show")

    def test_call_next_completes_the_appointment_being_served(self):
        token = self._issue()
        self._token_action(token, "call")
        self._token_action(token, "start-consultation")
        resp = self.client.post(f"/api/encounters/queue-tokens/call-next/{self.scope}")
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST))
        self.assertEqual(self._status(), "Completed")
