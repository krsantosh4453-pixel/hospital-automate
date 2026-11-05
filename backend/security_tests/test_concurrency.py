"""
Row locks under real parallel load (synthetic data only).

SQLite serialises every write, so these tests run only on PostgreSQL:

    TEST_DATABASE_URL=postgres://user:pass@localhost:5432/hms_test \\
        python manage.py test security_tests.test_concurrency

Each scenario starts several threads on their own database connections,
releases them together with a barrier and checks that the locked path let
exactly the right number through.
"""

import os
import threading
import unittest
from decimal import Decimal

from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from billing.models import Invoice, InvoiceItem, Payment
from billing.services import record_payment
from clinical.models import Prescription, PrescriptionItem
from doctors.models import Doctor
from hospital.models import Bed, Hospital, Room, Ward
from ipd.models import Admission, BedAllocation
from patients.models import Patient, PatientHospital
from pharmacy.models import Medicine, Sale
from users.models import StaffRole

from .test_tenant_isolation import make_staff

THREADS = 8


def run_together(target, count=THREADS):
    """Run ``target(index)`` in ``count`` threads that start at the same moment; return the results."""
    barrier = threading.Barrier(count)
    results = [None] * count

    def worker(index):
        try:
            barrier.wait()
            results[index] = target(index)
        except Exception as exc:  # collected for the assertions
            results[index] = exc
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


class WardMixin:
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Race", is_active=True)

    def make_patient(self, index):
        patient = Patient.objects.create(name=f"Synthetic Race {index}", age=40, gender="Male",
                                         phone=f"90009{index:05d}", hospital=self.hospital)
        PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid=f"RACE-{index}")
        return patient

    def bed_setup(self, beds):
        doctor_user, _ = make_staff("race_doctor", self.hospital, role=StaffRole.DOCTOR)
        doctor = Doctor.objects.create(hospital=self.hospital, user=doctor_user, name="Dr Race",
                                       specialization="General", phone="9000099999")
        room = Room.objects.create(ward=Ward.objects.create(hospital=self.hospital, name="Race Ward"),
                                   room_number="R1")
        return doctor_user, doctor, [Bed.objects.create(room=room, bed_number=f"B{i}", status="Available")
                                     for i in range(beds)]

    def post(self, user, admission, verb, bed):
        client = APIClient()
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client.post(f"/api/ipd/admissions/{admission.id}/{verb}/", {"bed_id": bed.id},
                           format="json").status_code

    def admitted_in(self, bed, doctor):
        admission = Admission.objects.create(patient=self.make_patient(99), hospital=self.hospital,
                                             admitting_doctor=doctor)
        BedAllocation.objects.create(admission=admission, bed=bed, is_active=True)
        Bed.objects.filter(pk=bed.pk).update(status="Occupied")
        return admission


class BedTransferTests(WardMixin, TestCase):
    def test_refused_transfer_leaves_the_patient_in_their_bed(self):
        user, doctor, [current, taken] = self.bed_setup(beds=2)
        Bed.objects.filter(pk=taken.pk).update(status="Occupied")
        admission = self.admitted_in(current, doctor)

        self.assertEqual(self.post(user, admission, "transfer", taken), 400)

        current.refresh_from_db()
        self.assertEqual(current.status, "Occupied")
        self.assertTrue(BedAllocation.objects.filter(admission=admission, bed=current, is_active=True).exists())


class RowLockSuiteGuardTests(TestCase):
    """CI sets REQUIRE_ROW_LOCK_TESTS=1 on its PostgreSQL run so the tests below can never skip silently."""

    def test_row_lock_tests_are_not_skipped_when_required(self):
        if os.environ.get("REQUIRE_ROW_LOCK_TESTS") == "1":
            self.assertEqual(connection.vendor, "postgresql", "row-lock tests need TEST_DATABASE_URL (PostgreSQL)")


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ConcurrentWriteTests(WardMixin, TransactionTestCase):

    def make_invoice(self, number):
        invoice = Invoice.objects.create(patient=self.make_patient(0), hospital=self.hospital,
                                         invoice_number=number, total=Decimal("100.00"))
        # recalculate() derives the total from the items.
        InvoiceItem.objects.create(invoice=invoice, description="Consult", quantity=1,
                                   unit_price=Decimal("100.00"), subtotal=Decimal("100.00"))
        return invoice

    def test_parallel_payments_never_exceed_the_invoice_total(self):
        invoice = self.make_invoice("INV-RACE-1")

        results = run_together(lambda i: record_payment(invoice, Decimal("50.00")))

        accepted = [r for r in results if isinstance(r, tuple)]
        refused = [r for r in results if isinstance(r, ValidationError)]
        self.assertEqual((len(accepted), len(refused)), (2, THREADS - 2), results)
        self.assertEqual(sum(p.amount for p in Payment.objects.filter(invoice=invoice)), Decimal("100.00"))

    def test_parallel_retries_with_one_idempotency_key_charge_once(self):
        invoice = self.make_invoice("INV-RACE-2")

        results = run_together(lambda i: record_payment(invoice, Decimal("10.00"), idempotency_key="retry-1"))

        self.assertTrue(all(isinstance(r, tuple) for r in results), results)
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)

    def test_parallel_adjustments_never_spend_more_advance_than_was_deposited(self):
        # H4: 100 in advance, eight bills of 100 each, eight adjustments of 50 at once.
        from billing import advances
        from billing.models import AdvanceAccount

        patient = self.make_patient(0)
        advances.record_deposit(self.hospital.id, patient.id, Decimal("100.00"))
        invoices = []
        for i in range(THREADS):
            invoice = Invoice.objects.create(patient=patient, hospital=self.hospital, invoice_number=f"INV-ADV-{i}",
                                             total=Decimal("100.00"))
            InvoiceItem.objects.create(invoice=invoice, description="Consult", quantity=1,
                                       unit_price=Decimal("100.00"), subtotal=Decimal("100.00"))
            invoices.append(invoice)

        results = run_together(lambda i: advances.apply_to_invoice(invoices[i], Decimal("50.00")))

        accepted = [r for r in results if isinstance(r, tuple)]
        self.assertEqual(len(accepted), 2, results)
        self.assertEqual(AdvanceAccount.objects.get(patient=patient).balance, Decimal("0.00"))
        self.assertEqual(sum(p.amount for p in Payment.objects.filter(invoice__in=invoices)), Decimal("100.00"))

    def test_parallel_deposit_retries_with_one_key_count_once(self):
        from billing import advances
        from billing.models import AdvanceAccount

        patient = self.make_patient(0)
        results = run_together(lambda i: advances.record_deposit(self.hospital.id, patient.id, Decimal("500.00"),
                                                                 idempotency_key="adv-retry"))
        self.assertTrue(all(isinstance(r, tuple) for r in results), results)
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(AdvanceAccount.objects.get(patient=patient).balance, Decimal("500.00"))

    def test_one_bed_goes_to_exactly_one_of_many_admissions(self):
        user, doctor, [bed] = self.bed_setup(beds=1)
        admissions = [Admission.objects.create(patient=self.make_patient(i), hospital=self.hospital,
                                               admitting_doctor=doctor) for i in range(THREADS)]

        statuses = run_together(lambda i: self.post(user, admissions[i], "allocate_bed", bed))

        self.assertEqual(statuses.count(201), 1, statuses)
        self.assertEqual(BedAllocation.objects.filter(bed=bed, is_active=True).count(), 1)

    def test_one_admission_gets_exactly_one_of_many_beds(self):
        user, doctor, beds = self.bed_setup(beds=THREADS)
        admission = Admission.objects.create(patient=self.make_patient(0), hospital=self.hospital,
                                             admitting_doctor=doctor)

        statuses = run_together(lambda i: self.post(user, admission, "allocate_bed", beds[i]))

        self.assertEqual(statuses.count(201), 1, statuses)
        self.assertEqual(BedAllocation.objects.filter(admission=admission, is_active=True).count(), 1)
        self.assertEqual(Bed.objects.filter(status="Occupied").count(), 1)

    def test_parallel_transfers_leave_the_patient_in_one_bed(self):
        user, doctor, [current, *targets] = self.bed_setup(beds=THREADS + 1)
        admission = self.admitted_in(current, doctor)

        # The lock serialises the transfers, so each may succeed in turn;
        # what must hold is that the patient ends in exactly one bed.
        statuses = run_together(lambda i: self.post(user, admission, "transfer", targets[i]))

        self.assertTrue(set(statuses) <= {201, 400}, statuses)
        self.assertEqual(BedAllocation.objects.filter(admission=admission, is_active=True).count(), 1)
        self.assertEqual(Bed.objects.filter(status="Occupied").count(), 1)

    # Pharmacy: dispensing a whole prescription (G-9)

    def dispense_setup(self, prescriptions, stock, per_item=10):
        pharmacist, _ = make_staff("race_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        medicine = Medicine.objects.create(name="Paracetamol", hospital=self.hospital, batch="RACE-P1",
                                           quantity=stock, price=Decimal("2.00"))
        rx_items = []
        for index in range(prescriptions):
            prescription = Prescription.objects.create(hospital=self.hospital, patient=self.make_patient(index))
            item = PrescriptionItem.objects.create(prescription=prescription, name="Paracetamol", quantity=per_item)
            rx_items.append((prescription, item))
        return pharmacist, medicine, rx_items

    def dispense(self, user, prescription, item, medicine):
        client = APIClient()
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client.post("/api/pharmacy-sales/dispense-prescription/", {
            "prescription": prescription.id, "lines": [{"item": item.id, "medicine": medicine.id}],
        }, format="json").status_code

    def test_one_prescription_is_dispensed_once_however_many_try(self):
        user, medicine, [(prescription, item)] = self.dispense_setup(prescriptions=1, stock=100)

        statuses = run_together(lambda i: self.dispense(user, prescription, item, medicine))

        self.assertEqual((statuses.count(201), statuses.count(409)), (1, THREADS - 1), statuses)
        medicine.refresh_from_db()
        self.assertEqual(medicine.quantity, 90)
        self.assertEqual(Sale.objects.filter(prescription=prescription).count(), 1)

    def test_parallel_dispenses_never_oversell_and_roll_back_cleanly(self):
        # Stock for two prescriptions of 10; eight pharmacists try at once.
        user, medicine, rx_items = self.dispense_setup(prescriptions=THREADS, stock=25)

        statuses = run_together(lambda i: self.dispense(user, *rx_items[i], medicine))

        self.assertEqual((statuses.count(201), statuses.count(400)), (2, THREADS - 2), statuses)
        medicine.refresh_from_db()
        self.assertEqual(medicine.quantity, 5)
        self.assertEqual(Sale.objects.filter(medicine=medicine).count(), 2)
        # A refused dispense leaves its prescription undispensed (the mark rolled back).
        self.assertEqual(Prescription.objects.filter(dispensed_at__isnull=False).count(), 2)

