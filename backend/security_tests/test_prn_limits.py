"""
H-10 (clinical hazard register): an as-needed (PRN) order may carry a
minimum time between doses and a maximum number of doses in 24 hours.
Before this change a nurse could record any number of PRN doses at any
interval. Synthetic data only.
"""

import datetime
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import Prescription, PrescriptionItem
from hospital.models import Hospital
from ipd.models import Admission
from nurses.models import MAR, MARAdministration
from nurses.prn_limits import prn_limit_refusal
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_in_care


class PrnLimitTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic PRN", is_active=True)
        self.nurse, _ = make_staff("prn_nurse", self.hospital, role=StaffRole.NURSE)
        self.doctor, _ = make_staff("prn_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.patient = Patient.objects.create(name="Synthetic PRN Patient", age=60, gender="Female",
                                              phone="9000000090", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="PRN-1")
        self.admission = Admission.objects.create(patient=self.patient, hospital=self.hospital, status="Admitted")
        self.rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        self.item = PrescriptionItem.objects.create(prescription=self.rx, name="Synthetic Paracetamol",
                                                    dosage="500 mg")
        put_in_care(self.doctor, self.hospital, self.patient)
        put_in_care(self.nurse, self.hospital, self.patient)
        self.order = self.mar("PRN", prn_min_interval_minutes=240, prn_max_doses_per_24h=3)
        self.nurse_client = self.client_for(self.nurse)
        self.doctor_client = self.client_for(self.doctor)

    def mar(self, frequency, **limits):
        return MAR.objects.create(patient=self.patient, admission=self.admission, hospital=self.hospital,
                                  prescription=self.rx, prescription_item=self.item,
                                  medicine_name="Synthetic Paracetamol", dose="500 mg", route="Oral",
                                  frequency=frequency, start_date=datetime.date.today() - timedelta(days=1),
                                  end_date=datetime.date.today() + timedelta(days=2), **limits)

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def given(self, order, hours_ago, status=MARAdministration.ADMINISTERED):
        at = timezone.now() - timedelta(hours=hours_ago)
        return MARAdministration.objects.create(mar=order, scheduled_time=at, administered_time=at, status=status,
                                                is_prn=True)

    def give(self, order=None):
        order = order or self.order
        return self.nurse_client.post(f"/api/nurses/mar/{order.id}/prn/", {"notes": "Pain 6/10"}, format="json")

    def test_a_dose_inside_the_minimum_interval_is_refused_and_audited(self):
        self.given(self.order, hours_ago=1)
        response = self.give()
        self.assertEqual(response.status_code, 409, response.content)
        body = response.json()
        self.assertEqual(body["code"], "prn_min_interval")
        self.assertTrue(body["prn_min_interval"] and body["prn_limit"])
        self.assertIn("240 minutes", body["detail"])
        self.assertEqual(MARAdministration.objects.filter(mar=self.order).count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="nurses.mar.prn_refused").exists())

    def test_a_dose_after_the_interval_is_given(self):
        self.given(self.order, hours_ago=5)
        response = self.give()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(MARAdministration.objects.filter(mar=self.order, is_prn=True).count(), 2)

    def test_the_daily_maximum_counts_the_last_24_hours_only(self):
        for hours in (23, 17, 11):
            self.given(self.order, hours_ago=hours)
        refused = self.give()
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(refused.json()["code"], "prn_max_per_24h")
        self.assertTrue(refused.json()["prn_max_per_24h"])

        MARAdministration.objects.filter(mar=self.order).order_by("administered_time").first().delete()
        self.given(self.order, hours_ago=25)
        self.assertEqual(self.give().status_code, 201)

    def test_held_or_refused_doses_do_not_count(self):
        self.given(self.order, hours_ago=1, status="Refused")
        self.given(self.order, hours_ago=2, status="Held")
        self.assertEqual(self.give().status_code, 201)

    def test_an_order_without_limits_behaves_as_before(self):
        open_order = self.mar("SOS")
        self.given(open_order, hours_ago=0.1)
        self.assertEqual(self.give(open_order).status_code, 201)

    def test_the_interval_is_checked_against_the_time_of_the_request(self):
        last = self.given(self.order, hours_ago=0)
        later = last.administered_time + timedelta(minutes=239)
        self.assertEqual(prn_limit_refusal(self.order, later)["code"], "prn_min_interval")
        self.assertIsNone(prn_limit_refusal(self.order, last.administered_time + timedelta(minutes=240)))

    def test_the_order_row_is_locked_while_the_dose_is_checked(self):
        with mock.patch("nurses.views.MAR.objects.select_for_update", wraps=MAR.objects.select_for_update) as lock:
            self.assertEqual(self.give().status_code, 201)
        lock.assert_called_once()

    def test_the_doctor_sets_limits_only_on_an_as_needed_order(self):
        url = "/api/nurses/mar/"
        scheduled = self.mar("TID")
        bad = self.doctor_client.patch(f"{url}{scheduled.id}/", {"prn_min_interval_minutes": 240}, format="json")
        self.assertEqual(bad.status_code, 400, bad.content)
        self.assertIn("prn_min_interval_minutes", bad.json()["details"])

        for body in ({"prn_min_interval_minutes": 5}, {"prn_max_doses_per_24h": 0},
                     {"prn_max_doses_per_24h": 49}):
            with self.subTest(body=body):
                response = self.doctor_client.patch(f"{url}{self.order.id}/", body, format="json")
                self.assertEqual(response.status_code, 400, response.content)

        ok = self.doctor_client.patch(f"{url}{self.order.id}/", {"prn_min_interval_minutes": 360,
                                                                 "prn_max_doses_per_24h": 4}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.order.refresh_from_db()
        self.assertEqual((self.order.prn_min_interval_minutes, self.order.prn_max_doses_per_24h), (360, 4))

    def test_a_nurse_cannot_change_the_limits(self):
        response = self.nurse_client.patch(f"/api/nurses/mar/{self.order.id}/", {"prn_max_doses_per_24h": 10},
                                           format="json")
        self.assertEqual(response.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.prn_max_doses_per_24h, 3)
