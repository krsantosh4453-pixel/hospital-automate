"""
R-03: nothing clinical is erased. A removal marks the record entered in error,
with who, when and why, and the audit log keeps every edit's old values.
Synthetic data only.
"""

import json

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import Diagnosis, VitalSign
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_in_care


class EnteredInErrorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic EIE", is_active=True)
        cls.patient = Patient.objects.create(name="Synthetic EIE Patient", age=50, gender="Male",
                                             phone="9000000801", hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="EIE-1")
        cls.visit = Visit.objects.create(patient=cls.patient, hospital=cls.hospital)
        cls.doctor, _ = make_staff("eie_doctor", cls.hospital, role=StaffRole.DOCTOR)
        put_in_care(cls.doctor, cls.hospital, cls.patient)

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def test_removed_vitals_leave_the_list_but_stay_with_who_and_why(self):
        vital = VitalSign.objects.create(visit=self.visit, heart_rate=180)
        client = self.client_for(self.doctor)
        resp = client.delete(f"/api/clinical/vitals/{vital.id}/", {"reason": "Wrong patient's reading"}, format="json")
        self.assertEqual(resp.status_code, 204, resp.content)

        listed = client.get(f"/api/clinical/vitals/?visit={self.visit.id}")
        rows = listed.json().get("results", listed.json())
        self.assertNotIn(vital.id, [row["id"] for row in rows])
        self.assertEqual(client.get(f"/api/clinical/vitals/{vital.id}/").status_code, 404)

        kept = VitalSign.all_objects.get(pk=vital.pk)
        self.assertEqual(kept.heart_rate, 180)
        self.assertEqual(kept.entered_in_error_by, self.doctor)
        entry = AuditLog.objects.get(action="clinical.vitalsign.entered_in_error", object_id=str(vital.pk))
        self.assertEqual(entry.user, self.doctor)
        self.assertEqual(json.loads(entry.details)["before"]["heart_rate"], 180)

    def test_removal_without_a_reason_is_refused_and_changes_nothing(self):
        vital = VitalSign.objects.create(visit=self.visit, heart_rate=90)
        for body in ({}, {"reason": "  ok "}):
            resp = self.client_for(self.doctor).delete(f"/api/clinical/vitals/{vital.id}/", body, format="json")
            self.assertEqual(resp.status_code, 400, resp.content)
            self.assertIn("reason", resp.json().get("details", resp.json()))
        self.assertTrue(VitalSign.objects.filter(pk=vital.pk).exists())

    def test_an_edit_records_the_old_and_new_value_and_who(self):
        diagnosis = Diagnosis.objects.create(visit=self.visit, name="Gastritis")
        resp = self.client_for(self.doctor).patch(f"/api/clinical/diagnoses/{diagnosis.id}/",
                                                  {"name": "Peptic ulcer"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        entry = AuditLog.objects.get(action="clinical.diagnosis.update", object_id=str(diagnosis.pk))
        self.assertEqual(entry.user, self.doctor)
        self.assertEqual(json.loads(entry.details)["changes"]["name"], {"from": "Gastritis", "to": "Peptic ulcer"})

    def test_removed_patient_is_not_found_by_search(self):
        other = Patient.objects.create(name="Synthetic Removed Person", age=30, gender="Female",
                                       phone="9000000802", hospital=self.hospital)
        PatientHospital.objects.create(patient=other, hospital=self.hospital, uhid="EIE-2")
        other.mark_entered_in_error(self.doctor, "Test registration")
        resp = self.client_for(self.doctor).get("/api/patients/?search=Removed")
        rows = resp.json().get("results", resp.json())
        self.assertEqual([row for row in rows if row["id"] == other.id], [])
