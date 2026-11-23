"""
First-dose scheduling of ward medication orders (final E2E audit, 20 Nov 2026):
a once-daily order written at 07:32 got its first dose at 00:00 and showed as
Overdue at once. Covers the scheduling rules (nurses/scheduling.py), the order
API, the preview, hospital medication rounds and the overdue grace period.
"""

from datetime import date, datetime, time, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import Prescription, PrescriptionItem
from hospital.models import Hospital
from ipd.models import Admission
from nurses import scheduling
from nurses.frequency import parse_frequency
from nurses.models import MAR, MARAdministration, MedicationRound
from nurses.serializers import MARAdministrationSerializer
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

IST = ZoneInfo("Asia/Kolkata")
NEW_YORK = ZoneInfo("America/New_York")
ROUNDS = [time(8, 0), time(14, 0), time(20, 0)]


def ist(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute), tzinfo=IST)


DAY = date(2026, 11, 20)


class FirstDoseRulesTests(SimpleTestCase):
    """nurses/scheduling.py on its own: fixed clock, no database."""

    def first(self, freq, mode=None, when=None, rounds=ROUNDS, now=None, start=DAY, end=None, tz=IST):
        return scheduling.resolve_first_dose(parse_frequency(freq), mode, when, rounds, start, end,
                                             now=now or ist(DAY, 7, 32), tz=tz)

    def test_once_daily_written_at_0732_starts_at_the_next_round_not_midnight(self):
        first = self.first("OD")
        self.assertEqual((first.mode, first.at), ("next_round", ist(DAY, 8)))

    def test_next_round_after_the_last_round_of_the_day_is_tomorrow_morning(self):
        first = self.first("OD", now=ist(DAY, 21, 15))
        self.assertEqual(first.at, ist(DAY + timedelta(days=1), 8))

    def test_round_exactly_now_is_not_reused(self):
        self.assertEqual(self.first("OD", now=ist(DAY, 14)).at, ist(DAY, 20))

    def test_without_configured_rounds_the_doctor_must_choose(self):
        with self.assertRaises(scheduling.ScheduleError) as caught:
            self.first("OD", rounds=[])
        self.assertTrue(caught.exception.needs_choice)

    def test_explicit_next_round_without_rounds_is_refused(self):
        with self.assertRaises(scheduling.ScheduleError):
            self.first("BD", mode="next_round", rounds=[])

    def test_start_now(self):
        self.assertEqual(self.first("OD", mode="now").at, ist(DAY, 7, 32))

    def test_stat_defaults_to_now(self):
        self.assertEqual(self.first("STAT", rounds=[]).mode, "now")

    def test_more_than_once_a_day_keeps_starting_now(self):
        self.assertEqual(self.first("TDS", rounds=[]).mode, "now")

    def test_specific_time_is_the_hospital_clock(self):
        self.assertEqual(self.first("OD", mode="at", when="2026-11-20T18:30").at, ist(DAY, 18, 30))

    def test_specific_time_in_the_past_is_refused(self):
        with self.assertRaises(scheduling.ScheduleError):
            self.first("OD", mode="at", when="2026-11-20T00:00")

    def test_a_few_seconds_of_clock_difference_is_tolerated(self):
        self.assertEqual(self.first("OD", mode="at", when="2026-11-20T07:30").at, ist(DAY, 7, 30))

    def test_specific_time_needs_a_time(self):
        with self.assertRaises(scheduling.ScheduleError) as caught:
            self.first("OD", mode="at")
        self.assertTrue(caught.exception.needs_choice)

    def test_first_dose_after_the_order_ends_is_refused(self):
        with self.assertRaises(scheduling.ScheduleError):
            self.first("OD", now=ist(DAY, 21), end=DAY)

    def test_order_starting_later_takes_the_first_round_of_that_day(self):
        later = DAY + timedelta(days=3)
        self.assertEqual(self.first("OD", start=later).at, ist(later, 8))

    def test_start_now_before_the_order_starts_is_refused(self):
        with self.assertRaises(scheduling.ScheduleError):
            self.first("OD", mode="now", start=DAY + timedelta(days=1))

    def test_prn_has_no_first_dose(self):
        with self.assertRaises(scheduling.ScheduleError):
            self.first("PRN")

    def test_daily_doses_follow_the_first_dose_and_end_date(self):
        times = scheduling.dose_times(parse_frequency("OD"), ist(DAY, 8), DAY + timedelta(days=2), tz=IST)
        self.assertEqual(times, [ist(DAY, 8), ist(DAY + timedelta(days=1), 8), ist(DAY + timedelta(days=2), 8)])

    def test_eight_hourly_doses_cross_midnight(self):
        times = scheduling.dose_times(parse_frequency("TDS"), ist(DAY, 20), DAY + timedelta(days=1), tz=IST)
        self.assertEqual(times[:3], [ist(DAY, 20), ist(DAY + timedelta(days=1), 4), ist(DAY + timedelta(days=1), 12)])

    def test_daily_dose_keeps_its_clock_time_across_daylight_saving(self):
        # New York springs forward on 8 Mar 2026: 08:00 stays 08:00 local.
        first = datetime(2026, 3, 7, 8, tzinfo=NEW_YORK)
        times = scheduling.dose_times(parse_frequency("OD"), first, date(2026, 3, 9), tz=NEW_YORK)
        self.assertEqual([t.hour for t in times], [8, 8, 8])
        utc = ZoneInfo("UTC")
        # Same-zone subtraction is wall-clock in Python; the real gap is 23 hours.
        self.assertEqual(times[1].astimezone(utc) - times[0].astimezone(utc), timedelta(hours=23))

    def test_round_inside_a_daylight_saving_gap_moves_after_it(self):
        now = datetime(2026, 3, 8, 1, 0, tzinfo=NEW_YORK)
        first = self.first("OD", rounds=[time(2, 30)], now=now, start=date(2026, 3, 8), tz=NEW_YORK)
        self.assertEqual((first.at.hour, first.at.minute), (3, 30))


@override_settings(HOSPITAL_TIME_ZONE="Asia/Kolkata")
class FirstDoseApiTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Rounds Hospital", is_active=True)
        self.doctor, _ = make_staff("fd_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.nurse, _ = make_staff("fd_nurse", self.hospital, role=StaffRole.NURSE)
        self.admin, _ = make_staff("fd_admin", self.hospital, role=StaffRole.ADMIN)
        self.patient = Patient.objects.create(name="Synthetic Ward Patient", age=60, gender="Female",
                                              phone="9000003301", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="FD-1")
        self.admission = Admission.objects.create(patient=self.patient, hospital=self.hospital, status="Admitted")
        put_in_care(self.doctor, self.hospital, self.patient)
        self.rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        self.item = PrescriptionItem.objects.create(prescription=self.rx, name="Synthetic Pantoprazole",
                                                    dosage="40 mg", frequency="OD")
        self.clock = mock.patch("django.utils.timezone.now", return_value=ist(DAY, 7, 32))
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def api(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def rounds(self):
        for clock, label in zip(ROUNDS, ("Morning", "Afternoon", "Night")):
            MedicationRound.objects.create(hospital=self.hospital, time=clock, label=label)

    def body(self, **extra):
        return {"patient": self.patient.id, "admission": self.admission.id, "hospital": self.hospital.id,
                "prescription": self.rx.id, "prescription_item": self.item.id,
                "medicine_name": "Synthetic Pantoprazole", "dose": "40 mg", "route": "Oral", "frequency": "OD",
                "start_date": DAY.isoformat(), "end_date": (DAY + timedelta(days=2)).isoformat(), **extra}

    def doses(self):
        return list(MARAdministration.objects.order_by("scheduled_time").values_list("scheduled_time", flat=True))

    def test_order_with_next_round_schedules_from_0800_not_midnight(self):
        self.rounds()
        resp = self.api(self.doctor).post("/api/nurses/mar/", self.body(first_dose="next_round"), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self.doses()[0], ist(DAY, 8))
        self.assertEqual(len(self.doses()), 3)
        row = AuditLog.objects.get(action="nurses.mar.schedule_generated")
        self.assertIn("next_round", row.details)

    def test_first_dose_is_not_overdue_before_its_time_plus_grace(self):
        self.rounds()
        self.api(self.doctor).post("/api/nurses/mar/", self.body(first_dose="next_round"), format="json")
        dose = MARAdministration.objects.order_by("scheduled_time").first()
        self.assertFalse(MARAdministrationSerializer(dose).data["is_delayed"])  # 07:32, due 08:00
        with mock.patch("django.utils.timezone.now", return_value=ist(DAY, 8, 29)):
            self.assertFalse(MARAdministrationSerializer(dose).data["is_delayed"])
        with mock.patch("django.utils.timezone.now", return_value=ist(DAY, 8, 31)):
            self.assertTrue(MARAdministrationSerializer(dose).data["is_delayed"])
        with override_settings(MAR_OVERDUE_GRACE_MINUTES=60), \
                mock.patch("django.utils.timezone.now", return_value=ist(DAY, 8, 31)):
            self.assertFalse(MARAdministrationSerializer(dose).data["is_delayed"])

    def test_refused_first_dose_leaves_no_order_behind(self):
        resp = self.api(self.doctor).post("/api/nurses/mar/", self.body(first_dose=None), format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("first_dose", resp.content.decode())
        self.assertFalse(MAR.objects.exists())

    def test_past_specific_time_is_refused(self):
        resp = self.api(self.doctor).post(
            "/api/nurses/mar/", self.body(first_dose="at", first_dose_at="2026-11-20T00:00"), format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(MAR.objects.exists())

    def test_specific_time_and_start_now(self):
        api = self.api(self.doctor)
        api.post("/api/nurses/mar/", self.body(first_dose="at", first_dose_at="2026-11-20T16:45"), format="json")
        self.assertEqual(self.doses()[0], ist(DAY, 16, 45))
        MARAdministration.objects.all().delete()
        MAR.objects.all().delete()
        api.post("/api/nurses/mar/", self.body(first_dose="now"), format="json")
        self.assertEqual(self.doses()[0], ist(DAY, 7, 32))

    def test_old_app_sending_only_todays_date_no_longer_gets_midnight(self):
        self.rounds()
        mar = MAR.objects.create(patient=self.patient, admission=self.admission, hospital=self.hospital,
                                 prescription=self.rx, prescription_item=self.item, medicine_name="Synthetic",
                                 dose="40 mg", route="Oral", frequency="OD", start_date=DAY,
                                 end_date=DAY + timedelta(days=1))
        resp = self.api(self.doctor).post(f"/api/nurses/mar/{mar.id}/generate_schedule/",
                                          {"start_date": DAY.isoformat()}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.doses()[0], ist(DAY, 8))

    def test_regenerating_never_duplicates_and_keeps_recorded_doses(self):
        self.rounds()
        api = self.api(self.doctor)
        api.post("/api/nurses/mar/", self.body(first_dose="next_round"), format="json")
        mar = MAR.objects.get()
        first = MARAdministration.objects.order_by("scheduled_time").first()
        MARAdministration.objects.filter(pk=first.pk).update(status="Administered")
        with mock.patch("django.utils.timezone.now", return_value=ist(DAY, 9)):
            api.post(f"/api/nurses/mar/{mar.id}/generate_schedule/", {"first_dose": "next_round"}, format="json")
            api.post(f"/api/nurses/mar/{mar.id}/generate_schedule/", {"first_dose": "next_round"}, format="json")
        times = self.doses()
        self.assertEqual(len(times), len(set(times)))
        self.assertEqual(MARAdministration.objects.get(pk=first.pk).status, "Administered")
        with self.assertRaises(IntegrityError), transaction.atomic():
            MARAdministration.objects.create(mar=mar, scheduled_time=times[-1], status="Scheduled")

    def test_preview_shows_the_schedule_and_saves_nothing(self):
        self.rounds()
        resp = self.api(self.doctor).post("/api/nurses/mar/schedule-preview/", {
            "hospital": self.hospital.id, "frequency": "OD", "start_date": DAY.isoformat(),
            "end_date": (DAY + timedelta(days=2)).isoformat()}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["first_dose_mode"], "next_round")
        self.assertEqual(resp.data["first_dose_at"], ist(DAY, 8).isoformat())
        self.assertEqual(resp.data["dose_count"], 3)
        self.assertEqual(resp.data["rounds"], ["08:00", "14:00", "20:00"])
        self.assertFalse(MARAdministration.objects.exists())

    def test_preview_without_rounds_asks_the_doctor_to_choose(self):
        resp = self.api(self.doctor).post("/api/nurses/mar/schedule-preview/", {
            "hospital": self.hospital.id, "frequency": "OD"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(resp.data["first_dose_required"])

    def test_nurse_cannot_preview_or_schedule(self):
        resp = self.api(self.nurse).post("/api/nurses/mar/schedule-preview/", {
            "hospital": self.hospital.id, "frequency": "OD"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_rounds_are_configured_by_admin_only_and_never_duplicated(self):
        url = "/api/nurses/medication-rounds/"
        body = {"hospital": self.hospital.id, "time": "08:00", "label": "Morning"}
        self.assertEqual(self.api(self.nurse).post(url, body, format="json").status_code, 403)
        self.assertEqual(self.api(self.admin).post(url, body, format="json").status_code, 201)
        self.assertEqual(self.api(self.admin).post(url, body, format="json").status_code, 400)
        round_id = MedicationRound.objects.get().id
        moved = self.api(self.admin).patch(f"{url}{round_id}/", {"time": "09:00"}, format="json")
        self.assertEqual(moved.status_code, 400)
        off = self.api(self.admin).patch(f"{url}{round_id}/", {"is_active": False}, format="json")
        self.assertEqual(off.status_code, 200, off.content)
        self.assertEqual(self.api(self.nurse).get(f"{url}?hospital={self.hospital.id}").status_code, 200)


class StaleDischargedOrdersMigrationTests(TestCase):
    """nurses.0013: orders left active by discharges before the A1 fix are stopped, history kept."""

    def test_only_orders_of_discharged_stays_are_stopped(self):
        import importlib

        from django.apps import apps
        from django.utils import timezone as dj_timezone

        hospital = Hospital.objects.create(name="Synthetic Migration Hospital", is_active=True)
        patient = Patient.objects.create(name="Synthetic Migrated", age=50, gender="Male", phone="9000003401",
                                         hospital=hospital)
        rx = Prescription.objects.create(hospital=hospital, patient=patient)
        item = PrescriptionItem.objects.create(prescription=rx, name="Synthetic", quantity=1)
        left = Admission.objects.create(patient=patient, hospital=hospital, status="Discharged",
                                        discharge_date=dj_timezone.now())
        staying = Admission.objects.create(patient=patient, hospital=hospital, status="Admitted")

        def order(admission):
            return MAR.objects.create(patient=patient, admission=admission, hospital=hospital, prescription=rx,
                                      prescription_item=item, medicine_name="Synthetic", dose="1", route="Oral",
                                      frequency="OD", start_date=DAY)

        stale, current = order(left), order(staying)
        given = MARAdministration.objects.create(mar=stale, scheduled_time=ist(DAY, 8), status="Administered")

        migration = importlib.import_module("nurses.migrations.0013_stop_orders_of_discharged_stays")
        migration.stop_orders_of_discharged_stays(apps, None)

        stale.refresh_from_db()
        current.refresh_from_db()
        self.assertFalse(stale.is_active)
        self.assertIsNotNone(stale.end_date)
        self.assertTrue(current.is_active)
        self.assertEqual(MARAdministration.objects.get(pk=given.pk).status, "Administered")
