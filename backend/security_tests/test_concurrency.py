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
from doctors.models import Doctor
from hospital.models import Bed, Hospital, Room, Ward
from ipd.models import Admission, BedAllocation
from patients.models import Patient, PatientHospital
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
