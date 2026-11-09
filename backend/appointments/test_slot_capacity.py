"""Decision G: one patient per doctor slot by default; a doctor's slot_capacity allows more (synthetic data)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from appointments.views import _hospital_now
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

User = get_user_model()
APPOINTMENTS = "/api/appointments/"


class SlotCapacityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Slots", is_active=True)
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, name="Dr Slot", specialization="General",
                                           phone="9000070001")
        cls.reception, _ = make_staff("slot_reception", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.admin, _ = make_staff("slot_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.patients = []
        for index in range(4):
            login = User.objects.create_user(username=f"slot_patient_{index}")
            patient = Patient.objects.create(user=login, name=f"Synthetic Slot {index}", age=30, gender="Female",
                                             phone=f"900007100{index}", hospital=cls.hospital)
            PatientHospital.objects.create(patient=patient, hospital=cls.hospital, uhid=f"SLOT-{index}")
            cls.patients.append(patient)
        cls.day = (_hospital_now().date() + timedelta(days=1)).isoformat()

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def set_capacity(self, capacity):
        Doctor.objects.filter(pk=self.doctor.pk).update(slot_capacity=capacity)

    def staff_book(self, index, time="10:00"):
        return self.client_for(self.reception).post(APPOINTMENTS, {
            "hospital": self.hospital.id, "patient": self.patients[index].id, "doctor": self.doctor.id,
            "appointment_date": self.day, "appointment_time": time, "status": "Scheduled",
        }, format="json")

    def self_book(self, index, time="10:00"):
        return self.client_for(self.patients[index].user).post(f"{APPOINTMENTS}book/", {
            "doctor": self.doctor.id, "appointment_date": self.day, "appointment_time": time,
        }, format="json")

    def seats(self, time="10:00"):
        return sorted(Appointment.objects.filter(doctor=self.doctor, appointment_time=time,
                                                 status__in=Appointment.ACTIVE_STATUSES)
                      .values_list("slot_seat", flat=True))

    # Default: one patient per slot ------------------------------------------

    def test_a_doctor_takes_one_patient_per_slot_by_default(self):
        self.assertEqual(Doctor.objects.get(pk=self.doctor.pk).slot_capacity, 1)

    def test_reception_cannot_put_a_second_patient_in_a_slot(self):
        self.assertEqual(self.staff_book(0).status_code, 201)

        second = self.staff_book(1)

        self.assertEqual(second.status_code, 400, second.content)
        self.assertIn("appointment_time", str(second.content))
        self.assertEqual(self.seats(), [1])

    def test_a_patient_cannot_self_book_a_slot_reception_filled(self):
        self.assertEqual(self.staff_book(0).status_code, 201)

        self.assertEqual(self.self_book(1).status_code, 409)
        self.assertEqual(self.seats(), [1])

    def test_the_database_refuses_a_second_active_booking_in_a_one_patient_slot(self):
        common = {"hospital": self.hospital, "doctor": self.doctor, "appointment_date": self.day,
                  "appointment_time": "10:00", "status": "Scheduled"}
        Appointment.objects.create(patient=self.patients[0], **common)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(patient=self.patients[1], **common)

    # Configured capacity ----------------------------------------------------

    def test_capacity_two_takes_two_patients_then_refuses(self):
        self.set_capacity(2)

        self.assertEqual(self.staff_book(0).status_code, 201)
        self.assertEqual(self.self_book(1).status_code, 201)
        self.assertEqual(self.staff_book(2).status_code, 400)
        self.assertEqual(self.self_book(3).status_code, 409)
        self.assertEqual(self.seats(), [1, 2])

    def test_booking_options_show_capacity_and_remaining_places(self):
        self.set_capacity(2)
        self.assertEqual(self.staff_book(0).status_code, 201)

        def slot_10():
            body = self.client_for(self.patients[3].user).get(f"{APPOINTMENTS}booking-options/", {
                "hospital": self.hospital.id, "doctor": self.doctor.id, "date": self.day}).json()
            return next(slot for slot in body["slots"] if slot["time"] == "10:00")

        self.assertEqual(slot_10(), {"time": "10:00", "available": True, "capacity": 2, "remaining": 1})
        self.assertEqual(self.staff_book(1).status_code, 201)
        self.assertEqual(slot_10(), {"time": "10:00", "available": False, "capacity": 2, "remaining": 0})

    # Places follow the booking's life ---------------------------------------

    def test_cancelling_frees_the_place(self):
        first = self.staff_book(0).json()["id"]
        self.assertEqual(self.client_for(self.reception).post(f"{APPOINTMENTS}{first}/cancel/").status_code, 200)

        self.assertEqual(self.staff_book(1).status_code, 201)
        self.assertEqual(self.seats(), [1])

    def test_reactivating_a_cancelled_booking_into_a_full_slot_is_refused(self):
        first = self.staff_book(0).json()["id"]
        self.client_for(self.reception).post(f"{APPOINTMENTS}{first}/cancel/")
        self.assertEqual(self.staff_book(1).status_code, 201)

        revived = self.client_for(self.reception).patch(f"{APPOINTMENTS}{first}/", {"status": "Scheduled"},
                                                        format="json")

        self.assertEqual(revived.status_code, 400, revived.content)
        self.assertEqual(Appointment.objects.get(pk=first).status, "Cancelled")

    def test_rescheduling_into_a_full_slot_is_refused(self):
        self.assertEqual(self.staff_book(0, time="10:00").status_code, 201)
        moving = self.staff_book(1, time="10:15").json()["id"]

        moved = self.client_for(self.reception).post(f"{APPOINTMENTS}{moving}/reschedule/",
                                                     {"appointment_time": "10:00"}, format="json")

        self.assertEqual(moved.status_code, 400, moved.content)
        self.assertEqual(str(Appointment.objects.get(pk=moving).appointment_time)[:5], "10:15")

    def test_rescheduling_into_a_free_place_takes_it(self):
        self.set_capacity(2)
        self.staff_book(0, time="10:15")
        moving = self.staff_book(1, time="10:00").json()["id"]

        moved = self.client_for(self.reception).post(f"{APPOINTMENTS}{moving}/reschedule/",
                                                     {"appointment_time": "10:15"}, format="json")

        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(self.seats("10:15"), [1, 2])
        self.assertEqual(self.seats("10:00"), [])

    def test_editing_other_fields_keeps_the_place(self):
        self.set_capacity(2)
        self.staff_book(0)
        second = self.staff_book(1).json()["id"]

        edited = self.client_for(self.reception).patch(f"{APPOINTMENTS}{second}/", {"reason": "Follow-up"},
                                                       format="json")

        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual(Appointment.objects.get(pk=second).slot_seat, 2)

    def test_lowering_capacity_below_existing_bookings_refuses_new_ones(self):
        self.set_capacity(3)
        ids = [self.staff_book(index).json()["id"] for index in range(3)]
        self.client_for(self.reception).post(f"{APPOINTMENTS}{ids[1]}/cancel/")
        self.set_capacity(2)  # places 1 and 3 are still held

        self.assertEqual(self.staff_book(3).status_code, 400)
        self.assertEqual(self.seats(), [1, 3])

    # Queue tokens put back in the queue ------------------------------------

    def requeue_token_of(self, appointment):
        from encounters.models import QueueToken, Visit
        from encounters.services.appointment_status import sync_appointment_status

        visit = Visit.objects.create(hospital=self.hospital, patient=appointment.patient, doctor=self.doctor)
        token = QueueToken.objects.create(hospital=self.hospital, visit=visit, patient=appointment.patient,
                                          doctor=self.doctor, appointment=appointment,
                                          token_date=appointment.appointment_date, token_number=1,
                                          status=QueueToken.Status.WAITING)
        sync_appointment_status(token)
        appointment.refresh_from_db()
        return appointment

    def test_requeued_no_show_takes_a_free_place_again(self):
        missed = Appointment.objects.create(hospital=self.hospital, patient=self.patients[0], doctor=self.doctor,
                                            appointment_date=self.day, appointment_time="10:00", status="No Show")

        self.assertEqual(self.requeue_token_of(missed).status, "Checked In")
        self.assertEqual(self.seats(), [1])

    def test_requeued_no_show_does_not_overbook_a_slot_filled_meanwhile(self):
        missed = Appointment.objects.create(hospital=self.hospital, patient=self.patients[0], doctor=self.doctor,
                                            appointment_date=self.day, appointment_time="10:00", status="No Show")
        self.assertEqual(self.staff_book(1).status_code, 201)

        self.assertEqual(self.requeue_token_of(missed).status, "No Show")
        self.assertEqual(self.seats(), [1])

    def test_rescheduling_a_booking_cancelled_meanwhile_does_not_reactivate_it(self):
        moving = self.staff_book(0).json()["id"]
        Appointment.objects.filter(pk=moving).update(status="Cancelled")

        moved = self.client_for(self.reception).post(f"{APPOINTMENTS}{moving}/reschedule/",
                                                     {"appointment_time": "10:15"}, format="json")

        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(Appointment.objects.get(pk=moving).status, "Cancelled")

    # Who sets capacity, and its limits --------------------------------------

    def test_an_admin_sets_capacity_within_one_to_twenty(self):
        url = f"/api/doctors/{self.doctor.id}/"
        admin = self.client_for(self.admin)

        self.assertEqual(admin.patch(url, {"slot_capacity": 0}, format="json").status_code, 400)
        self.assertEqual(admin.patch(url, {"slot_capacity": 21}, format="json").status_code, 400)
        self.assertEqual(admin.patch(url, {"slot_capacity": 3}, format="json").status_code, 200)
        self.assertEqual(Doctor.objects.get(pk=self.doctor.pk).slot_capacity, 3)

    def test_reception_cannot_change_capacity(self):
        response = self.client_for(self.reception).patch(f"/api/doctors/{self.doctor.id}/", {"slot_capacity": 5},
                                                         format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Doctor.objects.get(pk=self.doctor.pk).slot_capacity, 1)

    def test_the_database_refuses_capacity_outside_the_limits(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Doctor.objects.filter(pk=self.doctor.pk).update(slot_capacity=0)
