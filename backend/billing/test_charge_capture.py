"""
BUG-07 (Android E2E 2026-11-19, synthetic data only): consultation, laboratory
and bed-day charges are captured from the work itself, priced from the price
list, never twice, and the final bill of a stay can no longer be an
unexplained ₹0.
"""

import unittest
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from audit.models import AuditLog
from billing.models import Invoice, InvoiceItem, InvoiceWaiver, ServicePrice
from billing.services import record_payment
from config.hospital_time import hospital_today
from encounters.models import QueueToken
from encounters.test_visit_lifecycle import LifecycleFixture, client_for
from hospital.models import Bed, Hospital, Room, Ward
from ipd import discharge
from ipd.models import Admission, BedAllocation, DischargePlan, DischargeSummary
from laboratory.models import LabTest
from patients.models import Patient, PatientHospital
from security_tests.test_concurrency import run_together
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

Token = QueueToken.Status
LONG_AGO = hospital_today() - timedelta(days=60)
TICKED = dict(medications_reconciled=True, patient_counselled=True, follow_up_arranged=True, documents_handed_over=True)


def add_price(hospital, category, code, amount, applies_to="", doctor=None, tax="0"):
    return ServicePrice.objects.create(
        hospital=hospital, category=category, code=code, name=code, applies_to=applies_to, doctor=doctor,
        unit_price=Decimal(amount), tax_rate=Decimal(tax), effective_from=LONG_AGO,
    )


class ConsultationChargeTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("fee")
        self.default_fee = add_price(self.hospital, "consultation", "CON-OPD", "500.00")

    def fee_lines(self, token):
        return InvoiceItem.objects.filter(charge_key=f"visit:{token.visit_id}:consultation")

    def test_completing_a_consultation_charges_the_fee_once(self):
        token = self.booked("FeeOnce", state=Token.IN_CONSULTATION)

        first = self.patch(self.doctor_user, token, "Completed")
        again = self.patch(self.doctor_user, token, "Completed")

        self.assertEqual((first.status_code, again.status_code), (200, 200))
        line = self.fee_lines(token).get()
        self.assertEqual((line.unit_price, line.category, line.service_price), (Decimal("500.00"), "consultation",
                                                                               self.default_fee))
        self.assertEqual((line.invoice.visit_id, line.invoice.total, line.invoice.status),
                         (token.visit_id, Decimal("500.00"), Invoice.Status.UNPAID))

    def test_completing_through_the_queue_token_charges_once(self):
        token = self.booked("FeeToken", state=Token.IN_CONSULTATION)
        client = client_for(self.doctor_user, self.hospital)

        done = client.post(f"/api/encounters/queue-tokens/{token.pk}/complete/")
        retry = client.post(f"/api/encounters/queue-tokens/{token.pk}/complete/")

        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(retry.status_code, 400)
        self.assertEqual(self.fee_lines(token).count(), 1)

    def test_the_doctors_own_fee_wins_over_the_hospital_default(self):
        add_price(self.hospital, "consultation", "CON-DR1", "800.00", doctor=self.doctor)
        token = self.booked("FeeDoctor", state=Token.IN_CONSULTATION)

        self.patch(self.doctor_user, token, "Completed")

        self.assertEqual(self.fee_lines(token).get().unit_price, Decimal("800.00"))

    def test_starting_or_cancelling_a_visit_charges_nothing(self):
        started = self.booked("FeeStart")
        waiting = self.booked("FeeCancel", state=Token.WAITING)

        self.assertEqual(self.patch(self.doctor_user, started, "In Consultation").status_code, 200)
        self.assertEqual(self.patch(self.admin_user, waiting, "Cancelled").status_code, 200)
        self.assertFalse(InvoiceItem.objects.filter(category="consultation").exists())

    def test_no_price_means_no_charge_and_an_audit_entry(self):
        ServicePrice.objects.all().delete()
        token = self.booked("FeeNone", state=Token.IN_CONSULTATION)

        self.assertEqual(self.patch(self.doctor_user, token, "Completed").status_code, 200)
        self.assertFalse(self.fee_lines(token).exists())
        self.assertTrue(AuditLog.objects.filter(action="billing.charge.unpriced", object_id=str(token.visit_id)).exists())

    def test_an_inpatients_consultation_goes_on_the_stay_bill(self):
        token = self.booked("FeeInpatient", state=Token.IN_CONSULTATION)
        admission = Admission.objects.create(patient=token.patient, hospital=self.hospital,
                                             admitting_doctor=self.doctor, status="Admitted")

        self.patch(self.doctor_user, token, "Completed")

        invoice = self.fee_lines(token).get().invoice
        self.assertEqual((invoice.admission, invoice.is_final), (admission, False))


class StayBillTests(TestCase):
    """A 3-day stay: 2 days in ICU at ₹5000, then 1 day in a general bed at ₹1000."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Stay Hospital", is_active=True)
        self.clerk, _ = make_staff("stay_clerk", self.hospital, role=StaffRole.BILLING_STAFF)
        self.manager, _ = make_staff("stay_manager", self.hospital, role=StaffRole.HOSPITAL_MANAGER)
        self.patient = Patient.objects.create(name="Synthetic Inpatient", age=61, gender="Female",
                                              phone="9000005001", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="SYN-S-1", is_active=True)
        room = Room.objects.create(ward=Ward.objects.create(hospital=self.hospital, name="Synthetic Ward"),
                                   room_number="S1")
        self.icu = Bed.objects.create(room=room, bed_number="ICU-1", bed_type="ICU", status="Available")
        self.general = Bed.objects.create(room=room, bed_number="G-1", bed_type="General", status="Occupied")
        add_price(self.hospital, "bed", "BED-GEN", "1000.00")
        add_price(self.hospital, "bed", "BED-ICU", "5000.00", applies_to="ICU")
        self.lab_price = add_price(self.hospital, "laboratory", "LAB-LIPID", "650.00", applies_to="Lipid Profile")
        self.admission = Admission.objects.create(patient=self.patient, hospital=self.hospital,
                                                  status="Discharge Initiated")
        start = timezone.now() - timedelta(days=2, hours=3)
        Admission.objects.filter(pk=self.admission.pk).update(admission_date=start)
        self.admission.refresh_from_db()
        icu = BedAllocation.objects.create(admission=self.admission, bed=self.icu, is_active=False)
        general = BedAllocation.objects.create(admission=self.admission, bed=self.general, is_active=True)
        moved = start + timedelta(days=1, hours=1)
        BedAllocation.objects.filter(pk=icu.pk).update(allocated_at=start, released_at=moved)
        BedAllocation.objects.filter(pk=general.pk).update(allocated_at=moved)

    def final_bill(self, body=None):
        return client_for(self.clerk, self.hospital).post(
            f"/api/ipd/admissions/{self.admission.pk}/final_bill/", body or {}, format="json")

    def verified_lab_test(self):
        from billing.charges import capture_lab_test
        from django.db import transaction

        test = LabTest.objects.create(hospital=self.hospital, name="Lipid Profile", patient=self.patient,
                                      status="Verified")
        with transaction.atomic():
            capture_lab_test(test)
        return test

    def make_ready(self):
        DischargePlan.objects.create(admission=self.admission, **TICKED)
        DischargeSummary.objects.create(admission=self.admission, summary="Recovered", finalized=True)

    def test_each_day_is_charged_at_the_bed_occupied_at_its_start(self):
        response = self.final_bill()

        self.assertEqual(response.status_code, 201, response.content)
        invoice = Invoice.objects.get(pk=response.data["id"])
        lines = list(invoice.items.values_list("description", "quantity", "unit_price", "category"))
        self.assertEqual(lines, [
            ("Bed charges (ICU, ₹5000.00/day): 2 day(s)", 2, Decimal("5000.00"), "bed"),
            ("Bed charges (General, ₹1000.00/day): 1 day(s)", 1, Decimal("1000.00"), "bed"),
        ])
        # 2 x 5000 + 1 x 1000 = 11000.00, no GST on these bed rates.
        self.assertEqual((invoice.total, invoice.is_final, invoice.status), (Decimal("11000.00"), True, "Unpaid"))

    def test_stay_charges_collect_on_the_running_bill_that_becomes_final(self):
        test = self.verified_lab_test()
        running = InvoiceItem.objects.get(charge_key=f"labtest:{test.pk}").invoice
        self.assertEqual((running.admission, running.is_final, running.total), (self.admission, False,
                                                                                Decimal("650.00")))

        response = self.final_bill()

        self.assertEqual(response.data["id"], running.pk)
        running.refresh_from_db()
        self.assertEqual(running.total, Decimal("11650.00"))  # 650 lab + 11000 beds
        self.assertEqual(Invoice.objects.filter(admission=self.admission).count(), 1)

    def test_without_a_bed_price_nothing_is_billed(self):
        ServicePrice.objects.filter(category="bed").delete()

        response = self.final_bill()

        self.assertEqual(response.status_code, 400)
        self.assertIn("no bed charge", str(response.content))
        self.assertFalse(Invoice.objects.exists())

    def test_a_typed_rate_must_agree_with_the_price_list(self):
        self.assertEqual(self.final_bill({"daily_rate": "1"}).status_code, 400)
        self.assertEqual(self.final_bill({"items": [{"description": "Free", "unit_price": "0"}]}).status_code, 400)
        self.assertFalse(Invoice.objects.exists())

    def test_the_preview_shows_what_the_bed_days_come_to(self):
        rows = client_for(self.clerk, self.hospital).get("/api/ipd/admissions/awaiting_final_bill/").json()
        self.assertEqual(rows[0]["bed_charges"]["total"], "11000.00")
        self.assertEqual([line["days"] for line in rows[0]["bed_charges"]["lines"]], [2, 1])

    def test_an_unexplained_zero_final_bill_blocks_discharge(self):
        self.make_ready()
        Invoice.objects.create(patient=self.patient, hospital=self.hospital, admission=self.admission,
                               is_final=True, invoice_number="SYN-LEGACY-0")

        blockers = discharge.readiness(self.admission)["blockers"]

        self.assertIn("The final bill comes to ₹0 without an approved waiver.", blockers)

    def test_a_waived_final_bill_lets_the_discharge_complete(self):
        self.make_ready()
        invoice_id = self.final_bill().data["id"]
        waived = client_for(self.manager, self.hospital).post(
            f"/api/billing/invoices/{invoice_id}/waive/", {"reason": "Government scheme beneficiary"}, format="json")

        self.assertEqual(waived.status_code, 201, waived.content)
        self.assertEqual(InvoiceWaiver.objects.get(invoice_id=invoice_id).amount, Decimal("11000.00"))
        self.assertTrue(discharge.readiness(self.admission)["ready"])

    def test_a_charge_after_the_final_bill_must_be_paid_before_discharge(self):
        self.make_ready()
        final = Invoice.objects.get(pk=self.final_bill().data["id"])
        record_payment(final, final.total)
        test = self.verified_lab_test()

        later = InvoiceItem.objects.get(charge_key=f"labtest:{test.pk}").invoice
        blockers = discharge.readiness(self.admission)["blockers"]

        self.assertNotEqual(later.pk, final.pk)
        self.assertEqual((later.admission, later.is_final), (self.admission, False))
        self.assertEqual(blockers, [f"Bill {later.invoice_number} of this stay has ₹650.00 still due."])

    def test_cancelling_the_final_bill_frees_its_charges_for_the_replacement(self):
        first = self.final_bill().data["id"]
        url = f"/api/billing/invoices/{first}/cancel/"
        # Review fix: a clerk cannot make captured charges free by cancelling the bill.
        by_clerk = client_for(self.clerk, self.hospital).post(url, {"reason": "Wrong bed type"}, format="json")
        no_reason = client_for(self.manager, self.hospital).post(url, {}, format="json")
        cancelled = client_for(self.manager, self.hospital).post(url, {"reason": "Wrong bed type recorded"},
                                                                 format="json")
        replacement = self.final_bill()

        self.assertEqual((by_clerk.status_code, no_reason.status_code), (403, 400))
        self.assertEqual(cancelled.status_code, 200, cancelled.content)
        self.assertEqual(replacement.status_code, 201, replacement.content)
        self.assertEqual(Invoice.objects.get(pk=replacement.data["id"]).total, Decimal("11000.00"))
        # The cancelled bill keeps its lines, with voided keys.
        self.assertTrue(all("#void-" in key for key in
                            InvoiceItem.objects.filter(invoice_id=first).values_list("charge_key", flat=True)))

    def test_captured_lines_and_their_bill_cannot_be_edited_or_deleted(self):
        invoice_id = self.final_bill().data["id"]
        line = InvoiceItem.objects.filter(invoice_id=invoice_id).first()
        client = client_for(self.manager, self.hospital)

        self.assertEqual(client.patch(f"/api/billing/invoice-items/{line.pk}/", {"unit_price": "1.00"},
                                      format="json").status_code, 400)
        self.assertEqual(client.delete(f"/api/billing/invoice-items/{line.pk}/").status_code, 400)
        self.assertEqual(client.delete(f"/api/billing/invoices/{invoice_id}/").status_code, 400)
        self.assertEqual(Invoice.objects.get(pk=invoice_id).total, Decimal("11000.00"))


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ParallelChargeTests(LifecycleFixture, TransactionTestCase):
    """Retries that arrive at the same moment still charge once (row locks + unique charge key)."""

    def setUp(self):
        self.build("parfee")
        add_price(self.hospital, "consultation", "CON-OPD", "500.00")
        add_price(self.hospital, "laboratory", "LAB-LIPID", "650.00", applies_to="Lipid Profile")

    def test_parallel_completions_charge_the_consultation_once(self):
        token = self.booked("ParallelFee", state=Token.IN_CONSULTATION)

        codes = run_together(lambda i: self.patch(self.doctor_user, token, "Completed").status_code)

        self.assertEqual(set(codes), {200}, codes)
        self.assertEqual(InvoiceItem.objects.filter(charge_key=f"visit:{token.visit_id}:consultation").count(), 1)
        self.assertEqual(Invoice.objects.filter(visit_id=token.visit_id).count(), 1)

    def test_parallel_verifications_verify_and_charge_once(self):
        from laboratory.models import LabResult

        enterer, _ = make_staff("parfee_tech", self.hospital, role=StaffRole.LAB_STAFF)
        checkers = [make_staff(f"parfee_checker{n}", self.hospital, role=StaffRole.LAB_STAFF)[0] for n in range(4)]
        patient = Patient.objects.create(name="Synthetic Parallel Lab", age=30, gender="Male", phone="9000005099",
                                         hospital=self.hospital)
        test = LabTest.objects.create(hospital=self.hospital, name="Lipid Profile", patient=patient, status="Processing")
        client_for(enterer, self.hospital).post(f"/api/laboratory/{test.pk}/enter_result/", {"result_text": "LDL 99"},
                                                format="json")
        self.assertTrue(LabResult.objects.filter(lab_test=test).exists())

        codes = run_together(lambda i: client_for(checkers[i], self.hospital).post(
            f"/api/laboratory/{test.pk}/verify_result/", {}, format="json").status_code, count=len(checkers))

        self.assertEqual(sorted(codes), [200, 400, 400, 400], codes)
        self.assertEqual(InvoiceItem.objects.filter(charge_key=f"labtest:{test.pk}").count(), 1)
