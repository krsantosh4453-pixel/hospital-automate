"""
H-14 (clinical hazard register): reference ranges, abnormal flags and
critical-value follow-up for laboratory results. Synthetic data only.

Before this change the server stored whatever ranges and flags the client
typed (both apps send none), so no result was ever flagged and a critical
value reached nobody.
"""

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

from . import flags
from .models import LabReferenceRange, LabResult, LabTest

User = get_user_model()
BASE = "/api/laboratory/"
RANGES = "/api/laboratory/reference-ranges/"


def api(user):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    return client


def rows_of(response):
    body = response.json()
    return body["results"] if isinstance(body, dict) else body


class LabFixture(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Range Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        self.tech, _ = make_staff("rr_tech", self.hospital, role=StaffRole.LAB_STAFF)
        self.checker, _ = make_staff("rr_checker", self.hospital, role=StaffRole.LAB_STAFF)
        self.admin, _ = make_staff("rr_admin", self.hospital, role=StaffRole.ADMIN)
        self.other_admin, _ = make_staff("rr_other_admin", self.other, role=StaffRole.ADMIN)
        self.doctor_user, _ = make_staff("rr_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(user=self.doctor_user, hospital=self.hospital, name="Dr Synthetic Range",
                                            specialization="General", phone="9000007001")
        self.login = User.objects.create_user(username="rr_patient_login", password="Synthetic-Pass-123")
        self.patient = Patient.objects.create(name="Synthetic Range Patient", age=40, gender="Female",
                                              phone="9000007002", hospital=self.hospital, user=self.login)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="SYN-R-1", is_active=True)
        self.visit = Visit.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                          status="Completed")
        self.hb_any = self.range("Hb", low="13", high="17", critical_low="7", critical_high="20", unit="g/dL")
        self.hb_female = self.range("Hb", low="12", high="16", critical_low="7", critical_high="20", unit="g/dL",
                                    sex="Female")
        self.k = self.range("K", low="3.5", high="5.1", critical_low="2.5", critical_high="6.5", unit="mmol/L")

    def range(self, parameter, test_name="CBC", hospital=None, **limits):
        values = {k: Decimal(v) for k, v in limits.items() if k not in ("unit", "sex")}
        return LabReferenceRange.objects.create(hospital=hospital or self.hospital, test_name=test_name,
                                                parameter=parameter, unit=limits.get("unit", ""),
                                                sex=limits.get("sex", ""), **values)

    def order(self, name="CBC", status="Processing"):
        return LabTest.objects.create(hospital=self.hospital, name=name, patient=self.patient, doctor=self.doctor,
                                      visit=self.visit, status=status)

    def enter(self, test, result_data, user=None, **extra):
        body = {"result_text": "see values", "result_data": result_data, **extra}
        return api(user or self.tech).post(f"{BASE}{test.pk}/enter_result/", body, format="json",
                                           HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

    def verify(self, test):
        return api(self.checker).post(f"{BASE}{test.pk}/verify_result/", {}, format="json",
                                      HTTP_X_HOSPITAL_ID=str(self.hospital.pk))


class EvaluateTests(LabFixture):
    def test_flags_low_high_critical_and_normal(self):
        cases = {"6.5": "LL", "7": "LL", "11.9": "L", "12": "", "16": "", "16.1": "H", "20": "HH", "25": "HH"}
        for value, expected in cases.items():
            with self.subTest(value=value):
                result = flags.evaluate(self.hospital.pk, "CBC", "Female", {"Hb": value})
                self.assertEqual(result.details[0]["flag"], expected)
                self.assertEqual(result.has_critical, expected in flags.CRITICAL_FLAGS)

    def test_the_patients_sex_picks_the_range_and_any_is_the_fallback(self):
        female = flags.evaluate(self.hospital.pk, "CBC", "Female", {"Hb": "12.5"})
        male = flags.evaluate(self.hospital.pk, "CBC", "Male", {"Hb": "12.5"})
        self.assertEqual(female.details[0]["flag"], "")
        self.assertEqual(male.details[0]["flag"], "L")
        self.assertEqual(female.reference_ranges, {"Hb": "12-16 g/dL"})

    def test_test_and_parameter_names_match_without_case(self):
        result = flags.evaluate(self.hospital.pk, "cbc", "Female", {"hb": "5"})
        self.assertEqual(result.details[0]["flag"], "LL")

    def test_a_value_that_is_not_a_number_is_not_checked_rather_than_normal(self):
        result = flags.evaluate(self.hospital.pk, "CBC", "Female", {"Hb": "<5", "K": "haemolysed"})
        self.assertEqual([(d["checked"], d["flag"]) for d in result.details], [(False, ""), (False, "")])
        self.assertFalse(result.has_critical)

    def test_the_client_cannot_clear_or_rewrite_a_flag_the_server_computed(self):
        result = flags.evaluate(self.hospital.pk, "CBC", "Female", {"Hb": "5"},
                                client_ranges={"Hb": "1-100"}, client_flags=[])
        self.assertEqual(result.abnormal_flags, ["Hb"])
        self.assertEqual(result.reference_ranges, {"Hb": "12-16 g/dL"})

    def test_parameters_without_a_hospital_range_keep_what_the_lab_typed(self):
        result = flags.evaluate(self.hospital.pk, "CBC", "Female", {"Hb": "14", "ESR": "40"},
                                client_ranges={"ESR": "0-20"}, client_flags=["ESR"])
        self.assertEqual(result.reference_ranges, {"Hb": "12-16 g/dL", "ESR": "0-20"})
        self.assertEqual(result.abnormal_flags, ["ESR"])

    def test_another_hospitals_ranges_are_never_used(self):
        self.range("Hb", hospital=self.other, low="1", high="2")
        self.assertEqual(flags.evaluate(self.other.pk, "CBC", "Female", {"Hb": "14"}).details[0]["flag"], "H")
        self.assertEqual(flags.evaluate(self.hospital.pk, "CBC", "Female", {"Hb": "14"}).details[0]["flag"], "")

    def test_retired_ranges_are_ignored(self):
        LabReferenceRange.objects.filter(parameter="K").update(is_active=False)
        self.assertEqual(flags.evaluate(self.hospital.pk, "CBC", "Female", {"K": "9"}).details, [])


class CriticalResultWorkflowTests(LabFixture):
    def test_entered_result_is_flagged_by_the_server(self):
        test = self.order()
        response = self.enter(test, {"Hb": "6", "K": "4.0"}, abnormal_flags=[])
        self.assertEqual(response.status_code, 201, response.content)
        result = LabResult.objects.get(lab_test=test)
        self.assertTrue(result.has_critical)
        self.assertEqual(result.abnormal_flags, ["Hb"])
        self.assertEqual({d["parameter"]: d["flag"] for d in result.flag_details}, {"Hb": "LL", "K": ""})
        self.assertTrue(response.json()["lab_result"]["has_critical"])

    def test_a_later_range_change_does_not_alter_an_entered_result(self):
        test = self.order()
        self.enter(test, {"Hb": "11"})
        LabReferenceRange.objects.filter(pk=self.hb_female.pk).update(low=Decimal("10"))
        result = LabResult.objects.get(lab_test=test)
        self.assertEqual(result.reference_ranges["Hb"], "12-16 g/dL")
        self.assertEqual(result.abnormal_flags, ["Hb"])

    def test_a_verified_critical_value_is_audited_and_waits_on_the_worklist(self):
        test = self.order()
        self.enter(test, {"Hb": "6"})
        self.assertEqual(self.verify(test).status_code, 200)
        details = json.loads(AuditLog.objects.get(action="lab.result.critical").details)
        self.assertEqual(details["parameters"], ["Hb"])
        self.assertEqual(details["doctor"], self.doctor.pk)

        listed = api(self.doctor_user).get(f"{BASE}critical-results/?mine=1",
                                           HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        self.assertEqual(listed.status_code, 200, listed.content)
        self.assertEqual([r["id"] for r in rows_of(listed)], [test.pk])

    def test_an_unverified_or_normal_result_is_not_on_the_worklist(self):
        pending = self.order()
        self.enter(pending, {"Hb": "6"})
        normal = self.order()
        self.enter(normal, {"Hb": "14"})
        self.verify(normal)
        listed = api(self.doctor_user).get(f"{BASE}critical-results/", HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        self.assertEqual(rows_of(listed), [])

    def test_a_doctor_acknowledges_once_with_a_note(self):
        test = self.order()
        self.enter(test, {"K": "7.1"})
        self.verify(test)
        url = f"{BASE}{test.pk}/acknowledge_critical/"
        headers = {"HTTP_X_HOSPITAL_ID": str(self.hospital.pk)}
        self.assertEqual(api(self.doctor_user).post(url, {"note": ""}, format="json", **headers).status_code, 400)
        self.assertEqual(api(self.tech).post(url, {"note": "Informed"}, format="json", **headers).status_code, 403)
        response = api(self.doctor_user).post(url, {"note": "Repeat K, ECG ordered"}, format="json", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        result = LabResult.objects.get(lab_test=test)
        self.assertEqual(result.critical_acknowledged_by, self.doctor_user)
        self.assertEqual(result.critical_acknowledgement_note, "Repeat K, ECG ordered")
        self.assertTrue(AuditLog.objects.filter(action="lab.result.critical_acknowledged").exists())
        again = api(self.doctor_user).post(url, {"note": "again"}, format="json", **headers)
        self.assertEqual(again.status_code, 409)
        self.assertEqual(rows_of(api(self.doctor_user).get(f"{BASE}critical-results/", **headers)), [])

    def test_acknowledging_a_result_without_a_critical_value_is_refused(self):
        test = self.order()
        self.enter(test, {"Hb": "14"})
        self.verify(test)
        response = api(self.doctor_user).post(f"{BASE}{test.pk}/acknowledge_critical/", {"note": "fine"},
                                              format="json", HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        self.assertEqual(response.status_code, 400)

    def test_a_patient_cannot_read_the_worklist(self):
        response = api(self.login).get(f"{BASE}critical-results/")
        self.assertEqual(response.status_code, 403)


class ReferenceRangeApiTests(LabFixture):
    def post(self, user, body, hospital=None):
        hospital = hospital or self.hospital
        return api(user).post(RANGES, {"hospital": hospital.pk, **body}, format="json",
                              HTTP_X_HOSPITAL_ID=str(hospital.pk))

    def test_an_admin_adds_a_range_and_it_is_audited(self):
        response = self.post(self.admin, {"test_name": " Lipid Profile ", "parameter": "LDL", "high": "130",
                                          "critical_high": "300", "unit": "mg/dL"})
        self.assertEqual(response.status_code, 201, response.content)
        row = LabReferenceRange.objects.get(pk=response.json()["id"])
        self.assertEqual((row.test_name, row.created_by), ("Lipid Profile", self.admin))
        self.assertTrue(AuditLog.objects.filter(action="laboratory.labreferencerange.create").exists())

    def test_only_an_admin_writes_ranges_but_clinical_staff_read_them(self):
        body = {"test_name": "CBC", "parameter": "WBC", "low": "4", "high": "11"}
        self.assertEqual(self.post(self.tech, body).status_code, 403)
        self.assertEqual(self.post(self.doctor_user, body).status_code, 403)
        listed = api(self.doctor_user).get(f"{RANGES}?test=cbc&active=1", HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(rows_of(listed)), 3)

    def test_limits_out_of_order_or_missing_are_refused(self):
        for body in ({"low": "10", "high": "5"}, {"low": "5", "high": "10", "critical_low": "6"},
                     {"low": "5", "high": "5"}, {}):
            with self.subTest(body=body):
                response = self.post(self.admin, {"test_name": "CBC", "parameter": "PLT", **body})
                self.assertEqual(response.status_code, 400, response.content)

    def test_a_second_active_range_must_wait_until_the_first_is_retired(self):
        body = {"test_name": "cbc", "parameter": "k", "low": "3", "high": "5"}
        self.assertEqual(self.post(self.admin, body).status_code, 400)
        retire = api(self.admin).patch(f"{RANGES}{self.k.pk}/", {"is_active": False}, format="json",
                                       HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        self.assertEqual(retire.status_code, 200, retire.content)
        self.assertEqual(self.post(self.admin, body).status_code, 201)

    def test_ranges_are_never_deleted(self):
        response = api(self.admin).delete(f"{RANGES}{self.k.pk}/", HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        self.assertEqual(response.status_code, 405)

    def test_another_hospitals_admin_neither_sees_nor_edits_these_ranges(self):
        client = api(self.other_admin)
        headers = {"HTTP_X_HOSPITAL_ID": str(self.other.pk)}
        self.assertEqual(rows_of(client.get(RANGES, **headers)), [])
        edit = client.patch(f"{RANGES}{self.k.pk}/", {"high": "9"}, format="json", **headers)
        self.assertEqual(edit.status_code, 404)
        foreign = self.post(self.other_admin, {"test_name": "CBC", "parameter": "Na", "low": "135"},
                            hospital=self.hospital)
        self.assertEqual(foreign.status_code, 403)
