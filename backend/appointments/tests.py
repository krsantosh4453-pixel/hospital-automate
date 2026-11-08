"""Tests for appointments module."""

from datetime import date, time, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from appointments.models import Appointment

User = get_user_model()


class AppointmentAPITests(TestCase):
    """Tests for appointment API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="General")

        # Create staff user for Hospital A
        self.user = User.objects.create_user(
            username="receptionist_a",
            email="receptionist_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.RECEPTIONIST,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.RECEPTIONIST,
            is_active=True,
        )

        # Create doctor
        self.doctor = Doctor.objects.create(
            name="Dr. Test",
            specialization="General",
            phone="9876543210",
            email="doctor@hospital.com",
            hospital=self.hospital_a,
            department=self.dept,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Test Patient",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Create appointment
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 0),
            hospital=self.hospital_a,
            status="Scheduled",
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_list_url(self):
        return f"/api/appointments/?hospital={self.hospital_a.id}"

    def _get_detail_url(self, pk):
        return f"/api/appointments/{pk}/"

    def _get_action_url(self, pk, action):
        return f"/api/appointments/{pk}/{action}/?hospital={self.hospital_a.id}"

    def test_list_appointments_scoped_to_hospital(self):
        """Test appointment list is scoped to user's hospital."""
        response = self.client.get(self._get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.appointment.id)

    def test_create_appointment(self):
        """Test creating an appointment."""
        response = self.client.post(
            self._get_list_url(),
            {
                "patient": self.patient.id,
                "doctor": self.doctor.id,
                "appointment_date": str(date.today() + timedelta(days=2)),
                "appointment_time": "11:00",
                "hospital": self.hospital_a.id,
                "reason": "Follow-up",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "Scheduled")

    def test_cancel_appointment(self):
        """Test cancelling an appointment."""
        response = self.client.post(
            self._get_action_url(self.appointment.id, "cancel"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "Cancelled")

    def test_reschedule_appointment(self):
        """Test rescheduling an appointment."""
        response = self.client.post(
            self._get_action_url(self.appointment.id, "reschedule"),
            {
                "appointment_date": str(date.today() + timedelta(days=3)),
                "appointment_time": "14:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(str(self.appointment.appointment_date), str(date.today() + timedelta(days=3)))
        self.assertEqual(str(self.appointment.appointment_time), "14:00:00")


    # --- P1-04 / RL-10: one active booking per patient, doctor and slot ---------

    def book(self, patient=None, at="10:00"):
        return self.client.post(self._get_list_url(), {
            "patient": (patient or self.patient).id, "doctor": self.doctor.id, "hospital": self.hospital_a.id,
            "appointment_date": str(self.appointment.appointment_date), "appointment_time": at,
        }, format="json")

    def test_same_patient_doctor_and_slot_is_refused_and_named(self):
        response = self.book()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(f"A{self.appointment.id:03d}", str(response.data))
        self.assertEqual(Appointment.objects.count(), 1)

    def test_another_patient_may_share_the_slot(self):
        other = Patient.objects.create(name="Other Patient", age=40, gender="Female", phone="9876500011",
                                       hospital=self.hospital_a)
        PatientHospital.objects.create(patient=other, hospital=self.hospital_a, is_active=True)

        self.assertEqual(self.book(patient=other).status_code, status.HTTP_201_CREATED)

    def test_a_cancelled_slot_can_be_booked_again(self):
        Appointment.objects.filter(pk=self.appointment.pk).update(status="Cancelled")

        self.assertEqual(self.book().status_code, status.HTTP_201_CREATED)

    def test_reschedule_onto_an_existing_booking_is_refused(self):
        later = self.book(at="12:00")
        self.assertEqual(later.status_code, status.HTTP_201_CREATED, later.data)

        response = self.client.post(self._get_action_url(later.data["id"], "reschedule"),
                                    {"appointment_time": "10:00"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(str(Appointment.objects.get(pk=later.data["id"]).appointment_time), "12:00:00")

    def test_the_database_refuses_a_duplicate_too(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(patient=self.patient, doctor=self.doctor, hospital=self.hospital_a,
                                       appointment_date=self.appointment.appointment_date,
                                       appointment_time=self.appointment.appointment_time)


class AppointmentModelTests(TestCase):
    """Tests for appointment model methods and constraints."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Test Hospital", is_active=True)
        self.dept = Department.objects.create(hospital=self.hospital, name="General")
        self.doctor = Doctor.objects.create(
            name="Dr. Test",
            specialization="General",
            phone="9876543210",
            email="doctor@hospital.com",
            hospital=self.hospital,
            department=self.dept,
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital,
        )

    def test_appointment_str(self):
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            hospital=self.hospital,
        )
        self.assertIn("Test Patient", str(appt))
        self.assertIn("Dr. Test", str(appt))