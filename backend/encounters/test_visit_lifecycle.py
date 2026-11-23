"""
BUG-02 (Android E2E 2026-11-19, synthetic data only): a visit's status change
moves its queue token and appointment with it.

Before: the Consultation screens PATCHed ``Visit.status`` and nothing else, so a
completed, admitted and discharged patient kept a Waiting token and a Checked
In appointment, stayed in the doctor's and nurse's queues, and the patient app
kept showing "position #2".
"""

import unittest
from datetime import time, timedelta
from unittest import mock

from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import QueueToken, Visit
from encounters.services.visit_lifecycle import close_open_tokens
from hospital.models import Hospital
from ipd.models import Admission
from patients.models import Patient, PatientHospital
from security_tests.test_concurrency import run_together
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

Token = QueueToken.Status


def client_for(user, hospital):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.pk))
    return client


class LifecycleFixture:
    """One hospital, two doctors, a desk, a nurse and synthetic booked patients."""

    def build(self, prefix):
        self.hospital = Hospital.objects.create(name=f"Synthetic {prefix} Hospital", is_active=True)
        self.doctor_user, _ = make_staff(f"{prefix}_doc", self.hospital, role=StaffRole.DOCTOR)
        self.colleague_user, _ = make_staff(f"{prefix}_col", self.hospital, role=StaffRole.DOCTOR)
        self.desk_user, _ = make_staff(f"{prefix}_desk", self.hospital, role=StaffRole.RECEPTIONIST)
        self.nurse_user, _ = make_staff(f"{prefix}_nurse", self.hospital, role=StaffRole.NURSE)
        self.admin_user, _ = make_staff(f"{prefix}_admin", self.hospital, role=StaffRole.ADMIN)
        self.doctor = Doctor.objects.create(user=self.doctor_user, hospital=self.hospital, name=f"Dr {prefix} One",
                                            specialization="General", phone="9000001001")
        self.colleague = Doctor.objects.create(user=self.colleague_user, hospital=self.hospital,
                                               name=f"Dr {prefix} Two", specialization="General", phone="9000001002")
        self.slot = 0

    def booked(self, name, state=Token.CALLED, doctor=None, day=None, number=None):
        """A patient with an appointment, a visit and a token in ``state``."""
        doctor = doctor or self.doctor
        day = day or hospital_today()
        self.slot += 1
        patient = Patient.objects.create(name=f"Synthetic {name}", age=40, gender="Female",
                                         phone=f"90000{self.slot:05d}", hospital=self.hospital)
        appointment = Appointment.objects.create(
            hospital=self.hospital, patient=patient, doctor=doctor, appointment_date=day,
            # Each booking its own 15-minute slot (one seat per slot).
            appointment_time=time(8 + self.slot // 4, (self.slot % 4) * 15), status=Appointment.Status.CHECKED_IN,
        )
        visit_state = "In Consultation" if state == Token.IN_CONSULTATION else "Waiting"
        visit = Visit.objects.create(hospital=self.hospital, patient=patient, doctor=doctor, status=visit_state)
        token = QueueToken.objects.create(
            hospital=self.hospital, visit=visit, appointment=appointment, patient=patient, doctor=doctor,
            token_date=day, token_number=number or self.slot, status=state,
        )
        return token

    def patch(self, user, token, new_status, **extra):
        return client_for(user, self.hospital).patch(
            f"/api/encounters/visits/{token.visit_id}/", {"status": new_status, **extra}, format="json",
        )

    def states(self, token):
        token = QueueToken.objects.select_related("visit", "appointment").get(pk=token.pk)
        return token.status, token.visit.status, token.appointment.status if token.appointment_id else None


class StartAndCompleteTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("lc")

    def test_start_moves_a_called_token_and_its_appointment_into_consultation(self):
        token = self.booked("Start")

        response = self.patch(self.doctor_user, token, "In Consultation")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "In Consultation")
        self.assertEqual(self.states(token), (Token.IN_CONSULTATION, "In Consultation", "In Consultation"))
        self.assertIsNotNone(QueueToken.objects.get(pk=token.pk).consultation_started_at)

    def test_complete_closes_visit_token_and_appointment_together(self):
        token = self.booked("Complete")
        self.patch(self.doctor_user, token, "In Consultation")

        response = self.patch(self.doctor_user, token, "Completed")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.states(token), (Token.COMPLETED, "Completed", "Completed"))
        self.assertIsNotNone(QueueToken.objects.get(pk=token.pk).completed_at)

    def test_a_waiting_token_is_never_called_automatically(self):
        token = self.booked("NotCalled", state=Token.WAITING)

        response = self.patch(self.doctor_user, token, "In Consultation")

        self.assertEqual(response.status_code, 409, response.content)
        self.assertTrue(response.json().get("patient_not_called"))
        self.assertEqual(self.states(token), (Token.WAITING, "Waiting", "Checked In"))
        self.assertIsNone(QueueToken.objects.get(pk=token.pk).called_at)

    def test_completing_twice_is_harmless(self):
        token = self.booked("Twice")
        self.patch(self.doctor_user, token, "In Consultation")
        self.patch(self.doctor_user, token, "Completed")
        completed_at = QueueToken.objects.get(pk=token.pk).completed_at

        again = self.patch(self.doctor_user, token, "Completed")

        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(QueueToken.objects.get(pk=token.pk).completed_at, completed_at)
        self.assertEqual(self.states(token), (Token.COMPLETED, "Completed", "Completed"))

    def test_a_completed_visit_is_not_reopened(self):
        token = self.booked("Reopen")
        self.patch(self.doctor_user, token, "In Consultation")
        self.patch(self.doctor_user, token, "Completed")

        for target in ("In Consultation", "Waiting", "Cancelled"):
            response = self.patch(self.doctor_user, token, target)
            self.assertEqual(response.status_code, 409, (target, response.content))
            self.assertTrue(response.json().get("invalid_transition"))
        self.assertEqual(self.states(token), (Token.COMPLETED, "Completed", "Completed"))

    def test_completing_without_starting_is_refused(self):
        token = self.booked("Skip")

        response = self.patch(self.doctor_user, token, "Completed")

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(self.states(token), (Token.CALLED, "Waiting", "Checked In"))

    def test_one_open_consultation_per_doctor(self):
        first = self.booked("First")
        second = self.booked("Second")
        self.patch(self.doctor_user, first, "In Consultation")

        response = self.patch(self.doctor_user, second, "In Consultation")

        self.assertEqual(response.status_code, 409, response.content)
        self.assertTrue(response.json().get("doctor_busy"))
        self.assertEqual(self.states(second), (Token.CALLED, "Waiting", "Checked In"))

    def test_unknown_status_is_a_bad_request(self):
        token = self.booked("Unknown")
        response = self.patch(self.admin_user, token, "Teleported")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(self.states(token), (Token.CALLED, "Waiting", "Checked In"))

    def test_a_token_left_waiting_by_the_old_direct_patch_is_closed_on_completion(self):
        # Data written before the fix: visit In Consultation, token still Waiting.
        token = self.booked("Legacy", state=Token.WAITING)
        Visit.objects.filter(pk=token.visit_id).update(status="In Consultation")

        response = self.patch(self.doctor_user, token, "Completed")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.states(token), (Token.COMPLETED, "Completed", "Completed"))

    def test_other_fields_are_saved_with_the_status(self):
        token = self.booked("Fields")
        response = self.patch(self.doctor_user, token, "In Consultation", chief_complaint="Synthetic cough")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Visit.objects.get(pk=token.visit_id).chief_complaint, "Synthetic cough")

    def test_a_visit_without_a_token_still_changes(self):
        patient = Patient.objects.create(name="Synthetic Walk-in", age=33, gender="Male", phone="9000001099",
                                         hospital=self.hospital)
        visit = Visit.objects.create(hospital=self.hospital, patient=patient, doctor=self.doctor)
        client = client_for(self.doctor_user, self.hospital)

        started = client.patch(f"/api/encounters/visits/{visit.pk}/", {"status": "In Consultation"}, format="json")
        done = client.patch(f"/api/encounters/visits/{visit.pk}/", {"status": "Completed"}, format="json")

        self.assertEqual((started.status_code, done.status_code), (200, 200))
        self.assertEqual(Visit.objects.get(pk=visit.pk).status, "Completed")


class CancelTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("cx")

    def test_cancelling_a_waiting_visit_cancels_its_token_and_booking(self):
        token = self.booked("CancelVisit", state=Token.WAITING)
        response = self.patch(self.desk_user, token, "Cancelled")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.states(token), (Token.CANCELLED, "Cancelled", "Cancelled"))

    def test_cancelling_an_appointment_takes_its_token_out_of_the_queue(self):
        token = self.booked("CancelBooking", state=Token.WAITING)
        response = client_for(self.desk_user, self.hospital).post(
            f"/api/appointments/{token.appointment_id}/cancel/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.states(token), (Token.CANCELLED, "Cancelled", "Cancelled"))

    def test_an_appointment_in_consultation_cannot_be_cancelled(self):
        token = self.booked("InRoom", state=Token.IN_CONSULTATION)
        response = client_for(self.desk_user, self.hospital).post(
            f"/api/appointments/{token.appointment_id}/cancel/")
        self.assertEqual(response.status_code, 409, response.content)
        self.assertTrue(response.json().get("patient_in_consultation"))
        self.assertEqual(self.states(token), (Token.IN_CONSULTATION, "In Consultation", "Checked In"))

    def test_patching_an_appointment_to_cancelled_cancels_its_token(self):
        token = self.booked("PatchCancel", state=Token.WAITING)
        response = client_for(self.desk_user, self.hospital).patch(
            f"/api/appointments/{token.appointment_id}/", {"status": "Cancelled"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.states(token), (Token.CANCELLED, "Cancelled", "Cancelled"))


class PermissionTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("pm")

    def test_only_the_visits_doctor_starts_or_completes_it(self):
        token = self.booked("Perms")
        for user in (self.desk_user, self.nurse_user, self.colleague_user):
            response = self.patch(user, token, "In Consultation")
            self.assertIn(response.status_code, (403, 404), (user.username, response.content))
        self.assertEqual(self.states(token), (Token.CALLED, "Waiting", "Checked In"))

    def test_an_admin_may_complete_a_stuck_consultation(self):
        token = self.booked("AdminFix", state=Token.IN_CONSULTATION)
        response = self.patch(self.admin_user, token, "Completed")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.states(token)[0], Token.COMPLETED)

    def test_another_hospitals_doctor_cannot_touch_the_visit(self):
        token = self.booked("Isolated")
        other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        outsider, _ = make_staff("pm_outsider", other, role=StaffRole.DOCTOR)
        Doctor.objects.create(user=outsider, hospital=other, name="Dr Outsider", specialization="", phone="")

        response = client_for(outsider, other).patch(
            f"/api/encounters/visits/{token.visit_id}/", {"status": "In Consultation"}, format="json")

        self.assertIn(response.status_code, (403, 404), response.content)
        self.assertEqual(self.states(token), (Token.CALLED, "Waiting", "Checked In"))

    def test_patients_cannot_change_visit_status(self):
        token = self.booked("PatientTry")
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="pm_patient", password="synthetic-Pass-123")
        Patient.objects.filter(pk=token.patient_id).update(user=user)
        PatientHospital.objects.create(patient_id=token.patient_id, hospital=self.hospital, uhid="SYN-PM-1")

        response = client_for(user, self.hospital).patch(
            f"/api/encounters/visits/{token.visit_id}/", {"status": "Completed"}, format="json")

        self.assertIn(response.status_code, (403, 404), response.content)
        self.assertEqual(self.states(token), (Token.CALLED, "Waiting", "Checked In"))


class QueueViewsTests(LifecycleFixture, TestCase):
    """What the patient, doctor and nurse screens read after a consultation."""

    def setUp(self):
        self.build("qv")

    def test_the_patient_sees_a_closed_token_after_completion(self):
        from django.contrib.auth.models import User
        token = self.booked("Viewer")
        user = User.objects.create_user(username="qv_patient", password="synthetic-Pass-123")
        Patient.objects.filter(pk=token.patient_id).update(user=user)
        PatientHospital.objects.create(patient_id=token.patient_id, hospital=self.hospital, uhid="SYN-QV-1")
        self.patch(self.doctor_user, token, "In Consultation")
        self.patch(self.doctor_user, token, "Completed")

        rows = client_for(user, self.hospital).get("/api/encounters/queue-tokens/").json()
        rows = rows.get("results", rows)

        self.assertEqual([row["status"] for row in rows], ["Completed"])

    def test_the_rest_of_the_queue_moves_up_after_a_completion(self):
        first = self.booked("Ahead", number=1)
        behind = self.booked("Behind", state=Token.WAITING, number=2)
        self.patch(self.doctor_user, first, "In Consultation")

        with self.captureOnCommitCallbacks(execute=True):
            self.patch(self.doctor_user, first, "Completed")

        waiting = client_for(self.doctor_user, self.hospital).get(
            f"/api/encounters/queue-tokens/?token_date={hospital_today()}&status=Waiting").json()
        waiting = waiting.get("results", waiting)
        self.assertEqual([row["id"] for row in waiting], [behind.pk])
        self.assertEqual(QueueToken.objects.get(pk=behind.pk).queue_position, 1)

    def test_dashboards_show_who_is_actually_being_seen(self):
        first = self.booked("Seen", number=1)
        self.booked("Later", state=Token.WAITING, number=2)
        stats_url = f"/api/home/stats/detail/?hospital={self.hospital.pk}"

        before = client_for(self.nurse_user, self.hospital).get(stats_url).data["statistics"]["queue"]
        self.patch(self.doctor_user, first, "In Consultation")
        during = client_for(self.nurse_user, self.hospital).get(stats_url).data["statistics"]["queue"]
        self.patch(self.doctor_user, first, "Completed")
        after = client_for(self.nurse_user, self.hospital).get(stats_url).data["statistics"]["queue"]

        self.assertEqual(before["current_token"], 0)  # nobody with a doctor yet
        self.assertEqual((during["current_token"], during["in_consultation"]), (1, 1))
        self.assertEqual((after["current_token"], after["waiting"], after["completed"]), (0, 1, 1))


class DischargeCleanupTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("dc")

    def admitted(self, token):
        return Admission.objects.create(hospital=self.hospital, patient_id=token.patient_id,
                                        admitting_doctor=self.doctor, status="Discharge Initiated",
                                        reason="Synthetic observation")

    def test_discharge_leaves_no_open_token(self):
        token = self.booked("Discharged", state=Token.WAITING)
        admission = self.admitted(token)
        with mock.patch("ipd.views.discharge.readiness", return_value={"ready": True, "blockers": []}):
            response = client_for(self.doctor_user, self.hospital).post(
                f"/api/ipd/admissions/{admission.pk}/complete_discharge/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Admission.objects.get(pk=admission.pk).status, "Discharged")
        self.assertEqual(self.states(token), (Token.CANCELLED, "Cancelled", "Cancelled"))

    def test_close_open_tokens_completes_a_consultation_and_keeps_later_follow_ups(self):
        in_room = self.booked("Room", state=Token.IN_CONSULTATION)
        patient_id = in_room.patient_id
        yesterday = self.booked("Old", state=Token.WAITING, day=hospital_today() - timedelta(days=1))
        QueueToken.objects.filter(pk=yesterday.pk).update(patient_id=patient_id)
        follow_up = self.booked("FollowUp", state=Token.WAITING, day=hospital_today() + timedelta(days=7))
        QueueToken.objects.filter(pk=follow_up.pk).update(patient_id=patient_id)

        closed = close_open_tokens(patient_id, self.hospital.pk, hospital_today())

        self.assertEqual({t.pk for t in closed}, {in_room.pk, yesterday.pk})
        self.assertEqual(self.states(in_room), (Token.COMPLETED, "Completed", "Completed"))
        self.assertEqual(QueueToken.objects.get(pk=yesterday.pk).status, Token.CANCELLED)
        self.assertEqual(QueueToken.objects.get(pk=follow_up.pk).status, Token.WAITING)

    def test_discharge_does_not_touch_another_hospitals_queue(self):
        token = self.booked("Home", state=Token.WAITING)
        other = Hospital.objects.create(name="Synthetic Elsewhere", is_active=True)
        other_doctor = Doctor.objects.create(hospital=other, name="Dr Elsewhere", specialization="", phone="")
        elsewhere_visit = Visit.objects.create(hospital=other, patient_id=token.patient_id, doctor=other_doctor)
        elsewhere = QueueToken.objects.create(hospital=other, visit=elsewhere_visit, patient_id=token.patient_id,
                                              doctor=other_doctor, token_date=hospital_today(), token_number=1)

        close_open_tokens(token.patient_id, self.hospital.pk, hospital_today())

        self.assertEqual(QueueToken.objects.get(pk=elsewhere.pk).status, Token.WAITING)


class StaleTokenRepairTests(LifecycleFixture, TestCase):
    """``close_stale_queue_tokens`` closes tokens the old direct PATCH left open."""

    def setUp(self):
        self.build("rp")

    def run_command(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("close_stale_queue_tokens", *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_dry_run_reports_and_changes_nothing(self):
        token = self.booked("DryRun", state=Token.WAITING)
        Visit.objects.filter(pk=token.visit_id).update(status="Completed")

        output = self.run_command()

        self.assertIn("Open tokens of closed visits: 1", output)
        self.assertNotIn("Synthetic", output)  # ids only, never names
        self.assertEqual(QueueToken.objects.get(pk=token.pk).status, Token.WAITING)

    def test_apply_closes_tokens_to_match_their_visits(self):
        done = self.booked("WasDone", state=Token.WAITING)
        Visit.objects.filter(pk=done.visit_id).update(status="Completed")
        dropped = self.booked("WasDropped", state=Token.CALLED)
        Visit.objects.filter(pk=dropped.visit_id).update(status="Cancelled")
        live = self.booked("StillWaiting", state=Token.WAITING)

        output = self.run_command("--apply")

        self.assertIn("Closed: 2. Still open: 0.", output)
        self.assertEqual(self.states(done), (Token.COMPLETED, "Completed", "Completed"))
        self.assertEqual(self.states(dropped), (Token.CANCELLED, "Cancelled", "Cancelled"))
        self.assertEqual(self.states(live), (Token.WAITING, "Waiting", "Checked In"))

    def test_a_later_appointments_token_on_an_old_visit_is_reported_not_closed(self):
        # Old token issuing put a second appointment's token on a finished visit.
        first = self.booked("Earlier", state=Token.COMPLETED)
        Visit.objects.filter(pk=first.visit_id).update(status="Completed")
        later = self.booked("Later", state=Token.WAITING)
        QueueToken.objects.filter(pk=later.pk).update(visit_id=first.visit_id, patient_id=first.patient_id)

        output = self.run_command("--apply")

        self.assertIn("not closed; cancel or reissue them): 1", output)
        self.assertEqual(QueueToken.objects.get(pk=later.pk).status, Token.WAITING)

        # Cancelling that later booking leaves the earlier, completed visit as it was.
        response = client_for(self.desk_user, self.hospital).post(
            f"/api/appointments/{later.appointment_id}/cancel/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(QueueToken.objects.get(pk=later.pk).status, Token.CANCELLED)
        self.assertEqual(Visit.objects.get(pk=first.visit_id).status, "Completed")


class TokenIssueVisitTests(LifecycleFixture, TestCase):
    """Issuing a token never puts a new appointment on a finished visit."""

    def setUp(self):
        self.build("ti")

    def test_a_completed_visit_of_an_earlier_appointment_is_not_reused(self):
        from encounters.services import issue_queue_token_for_appointment
        earlier = self.booked("Repeat", state=Token.COMPLETED)
        Visit.objects.filter(pk=earlier.visit_id).update(status="Completed")
        self.slot += 1
        second = Appointment.objects.create(
            hospital=self.hospital, patient_id=earlier.patient_id, doctor=self.doctor,
            appointment_date=hospital_today(), appointment_time=time(15, 30),
        )

        token, created = issue_queue_token_for_appointment(second)

        self.assertTrue(created)
        self.assertNotEqual(token.visit_id, earlier.visit_id)
        self.assertEqual(token.visit.status, "Waiting")

    def test_a_waiting_visit_opened_before_the_token_is_reused(self):
        from encounters.services import issue_queue_token_for_appointment
        patient = Patient.objects.create(name="Synthetic Desk First", age=50, gender="Male",
                                         phone="9000001098", hospital=self.hospital)
        visit = Visit.objects.create(hospital=self.hospital, patient=patient, doctor=self.doctor)
        appointment = Appointment.objects.create(
            hospital=self.hospital, patient=patient, doctor=self.doctor,
            appointment_date=hospital_today(), appointment_time=time(16, 0),
        )

        token, _ = issue_queue_token_for_appointment(appointment)

        self.assertEqual(token.visit_id, visit.pk)


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ParallelLifecycleTests(LifecycleFixture, TransactionTestCase):
    def setUp(self):
        self.build("par")

    def test_parallel_completions_complete_once(self):
        token = self.booked("ParallelDone", state=Token.IN_CONSULTATION)

        codes = run_together(lambda i: self.patch(self.doctor_user, token, "Completed").status_code)

        self.assertEqual(set(codes), {200}, codes)
        self.assertEqual(self.states(token), (Token.COMPLETED, "Completed", "Completed"))
        self.assertEqual(QueueToken.objects.filter(pk=token.pk, completed_at__isnull=False).count(), 1)

    def test_parallel_starts_for_one_doctor_open_one_consultation(self):
        tokens = [self.booked(f"ParallelStart{n}") for n in range(4)]

        codes = run_together(lambda i: self.patch(self.doctor_user, tokens[i], "In Consultation").status_code,
                             count=len(tokens))

        self.assertEqual(sorted(codes), [200, 409, 409, 409], codes)
        self.assertEqual(QueueToken.objects.filter(doctor=self.doctor, status=Token.IN_CONSULTATION).count(), 1)
        self.assertEqual(Visit.objects.filter(doctor=self.doctor, status="In Consultation").count(), 1)


class QueueAuditTests(LifecycleFixture, TestCase):
    """Final E2E audit gap: queue, visit and stay movements left no audit row."""

    def setUp(self):
        self.build("au")

    def actions(self, obj):
        from audit.models import AuditLog
        return list(AuditLog.objects.filter(object_id=str(obj.pk)).values_list("action", flat=True))

    def test_visit_and_token_changes_are_audited(self):
        token = self.booked("Audited")
        self.patch(self.doctor_user, token, "In Consultation")
        self.patch(self.doctor_user, token, "Completed")

        visit_actions = self.actions(token.visit)
        self.assertEqual(visit_actions.count("encounters.visit.status_changed"), 2)

    def test_token_actions_are_audited_with_from_and_to(self):
        from audit.models import AuditLog
        token = self.booked("Skipped", state=Token.WAITING)

        response = client_for(self.desk_user, self.hospital).post(f"/api/encounters/queue-tokens/{token.pk}/skip/")

        self.assertEqual(response.status_code, 200, response.content)
        row = AuditLog.objects.get(action="encounters.queue_token.status_changed", object_id=str(token.pk))
        import json
        self.assertEqual(json.loads(row.details), {"from": Token.WAITING, "to": Token.SKIPPED})

    def test_discharge_start_is_audited(self):
        token = self.booked("Stay", state=Token.COMPLETED)
        admission = Admission.objects.create(hospital=self.hospital, patient_id=token.patient_id,
                                             admitting_doctor=self.doctor, status="Admitted", reason="Synthetic")

        response = client_for(self.doctor_user, self.hospital).post(
            f"/api/ipd/admissions/{admission.pk}/initiate_discharge/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("ipd.admission.discharge_initiated", self.actions(admission))
