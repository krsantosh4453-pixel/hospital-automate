"""
BUG-06 (Android E2E 2026-11-19, synthetic data only): a laboratory result is
entered by one authorised user and verified by a different one. The original
result is never overwritten, the verifier and time are recorded, and only a
released result reaches the doctor and the patient. BUG-07: the test is
charged from the price list when, and only when, it is verified.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from billing.models import InvoiceItem, ServicePrice
from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

from .models import LabResult, LabTest, ResultVerification

User = get_user_model()
BASE = "/api/laboratory/"


class ResultVerificationTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Lab Hospital", is_active=True)
        self.tech, _ = make_staff("lab_tech", self.hospital, role=StaffRole.LAB_STAFF)
        self.checker, _ = make_staff("lab_checker", self.hospital, role=StaffRole.LAB_STAFF)
        self.admin, _ = make_staff("lab_admin", self.hospital, role=StaffRole.ADMIN)
        self.nurse, _ = make_staff("lab_nurse", self.hospital, role=StaffRole.NURSE)
        self.pharmacist, _ = make_staff("lab_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.doctor_user, _ = make_staff("lab_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(user=self.doctor_user, hospital=self.hospital, name="Dr Synthetic Lab",
                                            specialization="General", phone="9000006001")
        self.login = User.objects.create_user(username="lab_patient_login", password="Synthetic-Pass-123")
        self.patient = Patient.objects.create(name="Synthetic Lab Patient", age=52, gender="Male",
                                              phone="9000006002", hospital=self.hospital, user=self.login)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="SYN-L-1", is_active=True)
        self.visit = Visit.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                          status="Completed")
        self.price = ServicePrice.objects.create(
            hospital=self.hospital, category="laboratory", code="LAB-LIPID", name="Lipid profile",
            applies_to="Lipid Profile", unit_price=Decimal("650.00"), effective_from=hospital_today() - timedelta(days=5),
        )

    def order(self, status="Processing"):
        return LabTest.objects.create(hospital=self.hospital, name="Lipid Profile", patient=self.patient,
                                      doctor=self.doctor, visit=self.visit, status=status)

    def post(self, user, test, action, body=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        return client.post(f"{BASE}{test.pk}/{action}/", body or {}, format="json")

    def enter(self, test, user=None, text="LDL 162 mg/dL (high)"):
        return self.post(user or self.tech, test, "enter_result", {"result_text": text})

    def lab_charges(self, test):
        return InvoiceItem.objects.filter(charge_key=f"labtest:{test.pk}")

    def test_technician_enters_and_a_different_user_verifies(self):
        test = self.order()
        entered = self.enter(test)
        own = self.post(self.tech, test, "verify_result")

        self.assertEqual(entered.status_code, 201, entered.content)
        self.assertEqual(own.status_code, 403)
        self.assertTrue(own.json()["same_user"])
        test.refresh_from_db()
        self.assertEqual(test.status, "Result Entered")
        self.assertFalse(self.lab_charges(test).exists())

        verified = self.post(self.checker, test, "verify_result", {"comments": "Checked against analyser"})
        again = self.post(self.checker, test, "verify_result")

        self.assertEqual(verified.status_code, 200, verified.content)
        self.assertEqual(again.status_code, 400)
        result = LabResult.objects.get(lab_test=test)
        self.assertEqual((result.entered_by, result.verified_by, result.is_verified), (self.tech, self.checker, True))
        self.assertIsNotNone(result.verified_at)
        verification = ResultVerification.objects.get(lab_result=result)
        self.assertEqual((verification.verified_by, verification.self_verified), (self.checker, False))
        self.assertTrue(AuditLog.objects.filter(action="lab.result.verified", user=self.checker).exists())
        line = self.lab_charges(test).get()
        self.assertEqual((line.unit_price, line.category, line.service_price, line.invoice.visit),
                         (Decimal("650.00"), "laboratory", self.price, self.visit))

    def test_released_result_reaches_doctor_and_patient_only_after_release(self):
        test = self.order()
        self.enter(test)
        self.post(self.checker, test, "verify_result")
        portal = APIClient(raise_request_exception=False)
        portal.force_authenticate(self.login)

        self.assertEqual(self.post(self.tech, test, "release_result").status_code, 200)
        before_release = LabTest.objects.create(hospital=self.hospital, name="Lipid Profile", patient=self.patient,
                                                doctor=self.doctor, visit=self.visit, status="Verified")
        rows = portal.get(BASE).json()
        rows = rows.get("results", rows)
        doctor = APIClient(raise_request_exception=False)
        doctor.force_authenticate(self.doctor_user)
        doctor.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        seen = doctor.get(f"{BASE}{test.pk}/")

        self.assertEqual([row["id"] for row in rows], [test.pk])
        self.assertNotIn(before_release.pk, [row["id"] for row in rows])
        self.assertEqual(rows[0]["lab_result"]["result_text"], "LDL 162 mg/dL (high)")
        self.assertEqual(seen.status_code, 200)
        self.assertEqual(seen.json()["status"], "Released")

    def test_unauthorised_roles_cannot_enter_verify_or_release(self):
        test = self.order()
        for user in (self.nurse, self.doctor_user, self.pharmacist):
            with self.subTest(user=user.username):
                self.assertEqual(self.enter(test, user=user).status_code, 403)
        self.enter(test)
        for user in (self.nurse, self.doctor_user, self.pharmacist):
            with self.subTest(user=user.username):
                self.assertEqual(self.post(user, test, "verify_result").status_code, 403)
        self.post(self.checker, test, "verify_result")
        for user in (self.nurse, self.doctor_user, self.pharmacist):
            with self.subTest(user=user.username):
                self.assertEqual(self.post(user, test, "release_result").status_code, 403)
        test.refresh_from_db()
        self.assertEqual(test.status, "Verified")

    # Prompt 5 (SEC-002): every non-laboratory role is refused the second check.
    def test_no_other_staff_role_can_be_the_second_checker(self):
        test = self.order()
        self.enter(test)
        roles = (StaffRole.RECEPTIONIST, StaffRole.BILLING_STAFF, StaffRole.COMPOUNDER, StaffRole.RADIOLOGY_STAFF,
                 StaffRole.HOSPITAL_MANAGER, StaffRole.BLOOD_BANK_STAFF, StaffRole.INVENTORY_STAFF)
        for role in roles:
            user, _ = make_staff(f"p5_{role.lower().replace(' ', '_')}", self.hospital, role=role)
            with self.subTest(role=role):
                self.assertEqual(self.post(user, test, "verify_result").status_code, 403)
        outside = Hospital.objects.create(name="Synthetic Other Lab", is_active=True)
        stranger, _ = make_staff("p5_lab_other", outside, role=StaffRole.LAB_STAFF)
        self.assertIn(self.post(stranger, test, "verify_result").status_code, (403, 404))
        test.refresh_from_db()
        self.assertEqual(test.status, "Result Entered")
        self.assertFalse(ResultVerification.objects.exists())

    # Prompt 5 (SEC-002): POLICY DECISION REQUIRED. An Admin account can be the
    # second checker today (IsLabStaff includes Admin, as every role permission
    # does). Whether an Admin-only account may verify is a lab-director decision;
    # this test pins the current behaviour so a change is deliberate.
    def test_admin_can_currently_be_the_second_checker_pending_a_policy_decision(self):
        test = self.order()
        self.enter(test)
        self.assertEqual(self.post(self.admin, test, "verify_result").status_code, 200)
        self.assertEqual(LabResult.objects.get(lab_test=test).verified_by, self.admin)

    def test_the_entered_result_is_never_overwritten(self):
        test = self.order()
        self.enter(test, text="Original value")
        second = self.enter(test, user=self.checker, text="Different value")
        result = LabResult.objects.get(lab_test=test)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.tech)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        url = f"{BASE}lab-results/{result.pk}/"

        self.assertEqual(second.status_code, 409)
        self.assertEqual(client.patch(url, {"result_text": "edited", "is_verified": True}, format="json").status_code, 405)
        self.assertEqual(client.put(url, {"result_text": "edited"}, format="json").status_code, 405)
        self.assertEqual(client.delete(url).status_code, 405)
        self.assertEqual(client.post(f"{BASE}result-verifications/", {"lab_result": result.pk, "action": "Verified"},
                                     format="json").status_code, 405)
        result.refresh_from_db()
        self.assertEqual((result.result_text, result.is_verified, result.entered_by), ("Original value", False, self.tech))

    def test_an_empty_result_is_refused(self):
        test = self.order()
        self.assertEqual(self.enter(test, text="  ").status_code, 400)
        self.assertFalse(LabResult.objects.filter(lab_test=test).exists())

    def test_self_verification_only_under_an_admin_policy_and_it_is_audited(self):
        test = self.order()
        self.enter(test)
        policy_url = "verification-policy"
        client = APIClient(raise_request_exception=False)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        client.force_authenticate(self.tech)
        by_tech = client.post(f"{BASE}{policy_url}/", {"allow_self_verification": True, "reason": "Night shift"},
                              format="json")
        client.force_authenticate(self.admin)
        no_reason = client.post(f"{BASE}{policy_url}/", {"allow_self_verification": True}, format="json")
        allowed = client.post(f"{BASE}{policy_url}/", {"allow_self_verification": True,
                                                       "reason": "Single technician on the night shift"}, format="json")

        self.assertEqual(by_tech.status_code, 403)
        self.assertEqual(no_reason.status_code, 400)
        self.assertEqual(allowed.status_code, 200, allowed.content)
        verified = self.post(self.tech, test, "verify_result")
        self.assertEqual(verified.status_code, 200, verified.content)
        self.assertTrue(ResultVerification.objects.get(lab_result__lab_test=test).self_verified)
        audit = AuditLog.objects.get(action="lab.result.self_verified")
        self.assertIn("Single technician", audit.details)
        self.assertTrue(AuditLog.objects.filter(action="lab.verification_policy.update").exists())

    def test_tests_that_are_not_verified_are_never_charged(self):
        cancelled = self.order(status="Ordered")
        entered_only = self.order()
        self.enter(entered_only)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.doctor_user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertEqual(client.post(f"{BASE}{cancelled.pk}/cancel/").status_code, 200)
        self.assertFalse(InvoiceItem.objects.filter(category="laboratory").exists())

    def test_a_test_without_a_price_is_verified_but_not_billed_and_is_audited(self):
        self.price.delete()
        test = self.order()
        self.enter(test)

        self.assertEqual(self.post(self.checker, test, "verify_result").status_code, 200)
        self.assertFalse(self.lab_charges(test).exists())
        self.assertTrue(AuditLog.objects.filter(action="billing.charge.unpriced", object_id=str(test.pk)).exists())
