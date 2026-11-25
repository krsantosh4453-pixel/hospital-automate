"""
L-1: a wrong laboratory result is sent back before release instead of the
test being cancelled and ordered again. The values as entered are kept, the
test returns to Processing, and the corrected result goes through
maker-checker again. Synthetic data only.
"""

import json

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog

from .models import LabResult, LabResultRejection
from .test_result_verification import ResultVerificationTests


class ResultRejectionTests(TestCase):
    # Reuse the verification fixture without re-running its tests.
    setUp = ResultVerificationTests.setUp
    order = ResultVerificationTests.order
    post = ResultVerificationTests.post
    enter = ResultVerificationTests.enter
    lab_charges = ResultVerificationTests.lab_charges

    def reject(self, test, user=None, reason="Haemolysed sample, value implausible"):
        return self.post(user or self.checker, test, "reject_result", {"reason": reason})

    def test_an_entered_result_is_rejected_kept_and_entered_again(self):
        test = self.order()
        self.enter(test, text="LDL 1620 mg/dL")
        response = self.reject(test)
        self.assertEqual(response.status_code, 200, response.content)

        test.refresh_from_db()
        self.assertEqual((test.status, test.result), ("Processing", ""))
        self.assertFalse(LabResult.objects.filter(lab_test=test).exists())
        kept = LabResultRejection.objects.get(lab_test=test)
        self.assertEqual((kept.result_text, kept.entered_by, kept.rejected_by, kept.was_verified),
                         ("LDL 1620 mg/dL", self.tech, self.checker, False))
        details = json.loads(AuditLog.objects.get(action="lab.result.rejected").details)
        self.assertEqual(details["reason"], "Haemolysed sample, value implausible")

        # Entered again and verified by a different person, as usual.
        self.assertEqual(self.enter(test, text="LDL 162 mg/dL").status_code, 201)
        self.assertEqual(self.post(self.checker, test, "verify_result").status_code, 200)
        test.refresh_from_db()
        self.assertEqual(test.status, "Verified")

    def test_the_test_shows_how_often_it_was_sent_back(self):
        test = self.order()
        self.enter(test)
        self.reject(test, reason="Wrong units entered")
        # Nothing is entered now, so a second rejection is refused.
        self.assertEqual(self.reject(test).status_code, 400)
        client = APIClient()
        client.force_authenticate(self.checker)
        row = client.get(f"/api/laboratory/{test.pk}/", HTTP_X_HOSPITAL_ID=str(self.hospital.pk)).json()
        self.assertEqual((row["rejection_count"], row["last_rejection_reason"]), (1, "Wrong units entered"))

    def test_a_verified_result_can_be_rejected_without_a_second_charge(self):
        test = self.order()
        self.enter(test)
        self.post(self.checker, test, "verify_result")
        self.assertEqual(self.lab_charges(test).count(), 1)

        self.assertEqual(self.reject(test).status_code, 200)
        self.assertTrue(LabResultRejection.objects.get(lab_test=test).was_verified)
        self.enter(test, text="LDL 158 mg/dL")
        self.post(self.checker, test, "verify_result")
        self.assertEqual(self.lab_charges(test).count(), 1)

    def test_a_reason_is_required(self):
        test = self.order()
        self.enter(test)
        response = self.reject(test, reason="  bad ")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(LabResult.objects.filter(lab_test=test).exists())

    def test_a_released_result_cannot_be_rejected(self):
        test = self.order()
        self.enter(test)
        self.post(self.checker, test, "verify_result")
        self.post(self.checker, test, "release_result")
        response = self.reject(test)
        self.assertEqual(response.status_code, 400)
        test.refresh_from_db()
        self.assertEqual(test.status, "Released")
        self.assertFalse(LabResultRejection.objects.exists())

    def test_only_laboratory_staff_reject(self):
        test = self.order()
        self.enter(test)
        for user in (self.nurse, self.pharmacist, self.doctor_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.reject(test, user=user).status_code, 403)
        self.assertTrue(LabResult.objects.filter(lab_test=test).exists())
