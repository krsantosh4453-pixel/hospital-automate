"""Discharge checklist (E7) and the final bill of a stay (E12, H8)."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from billing.models import Invoice, ServicePrice
from billing.services import record_payment
from doctors.models import Doctor
from hospital.models import Hospital
from ipd.discharge import billable_days
from ipd.models import Admission, DischargePlan, DischargeSummary
from patients.models import Patient, PatientHospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
TICKED = dict(medications_reconciled=True, patient_counselled=True, follow_up_arranged=True, documents_handed_over=True)


def staff(username, hospital, role):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=username, is_active_staff=True)
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user


class DischargeReadinessTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Hospital A", is_active=True)
        self.other_hospital = Hospital.objects.create(name="Hospital B", is_active=True)
        self.doctor_user = staff("doc", self.hospital, StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, hospital=self.hospital, name="Dr A", specialization="General", phone="9000000000"
        )
        self.billing_user = staff("bill", self.hospital, StaffRole.BILLING_STAFF)
        self.patient = Patient.objects.create(name="Asha", age=40, gender="Female", phone="9999999999", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="U1", is_active=True)
        self.admission = Admission.objects.create(
            patient=self.patient, hospital=self.hospital, admitting_doctor=self.doctor, status="Discharge Initiated"
        )
        Admission.objects.filter(pk=self.admission.pk).update(admission_date=timezone.now() - timedelta(days=2, hours=3))
        self.admission.refresh_from_db()
        # BUG-07: bed days are priced from the hospital price list (general bed, ₹1000/day).
        ServicePrice.objects.create(
            hospital=self.hospital, category=ServicePrice.Category.BED, code="BED-GEN", name="General bed",
            unit_price=Decimal("1000.00"), effective_from=timezone.localdate() - timedelta(days=30),
        )
        self.client = APIClient()

    def url(self, action, detail=True):
        if detail:
            return f"/api/ipd/admissions/{self.admission.pk}/{action}/"
        return f"/api/ipd/admissions/{action}/"

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return {"HTTP_X_HOSPITAL_ID": str(self.hospital.pk)}

    def make_ready(self, pay=True):
        DischargePlan.objects.create(admission=self.admission, **TICKED)
        DischargeSummary.objects.create(admission=self.admission, summary="Recovered", finalized=True)
        response = self.client.post(self.url("final_bill"), {}, format="json", **self.as_user(self.billing_user))
        invoice = Invoice.objects.get(pk=response.data["id"])
        if pay:
            record_payment(invoice, invoice.total_amount)
        return invoice

    def test_partial_days_count_as_started_days(self):
        self.assertEqual(billable_days(self.admission), 3)

    def test_readiness_lists_every_blocker(self):
        response = self.client.get(self.url("readiness"), **self.as_user(self.doctor_user))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        blockers = response.data["blockers"]
        self.assertFalse(response.data["ready"])
        self.assertEqual(len([b for b in blockers if b.startswith("Checklist")]), 4)
        self.assertIn("No discharge plan has been written.", blockers)
        self.assertIn("A doctor must finalize the discharge summary.", blockers)
        self.assertIn("The final bill has not been created.", blockers)

    def test_unticked_checklist_item_blocks_discharge(self):
        self.make_ready()
        DischargePlan.objects.filter(admission=self.admission).update(follow_up_arranged=False)

        response = self.client.post(self.url("complete_discharge"), **self.as_user(self.doctor_user))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["blockers"], ["Checklist: Follow-up arranged."])

    def test_unpaid_final_bill_blocks_discharge(self):
        self.make_ready(pay=False)

        response = self.client.post(self.url("complete_discharge"), **self.as_user(self.doctor_user))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("still due", response.data["blockers"][0])

    def test_discharge_completes_when_everything_is_done(self):
        self.make_ready()

        response = self.client.post(self.url("complete_discharge"), **self.as_user(self.doctor_user))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.admission.refresh_from_db()
        self.assertEqual(self.admission.status, "Discharged")

    def test_discharge_stops_the_stay_medication_orders(self):
        """Doses of a discharged stay must not keep showing as due to nurses."""
        from clinical.models import Prescription, PrescriptionItem
        from nurses.models import MAR, MARAdministration

        self.make_ready()
        rx = Prescription.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor,
                                         status="Confirmed")
        item = PrescriptionItem.objects.create(prescription=rx, name="Synthetic Pantoprazole", quantity=5)
        order = MAR.objects.create(patient=self.patient, admission=self.admission, hospital=self.hospital,
                                   prescription=rx, prescription_item=item, medicine_name="Synthetic Pantoprazole",
                                   dose="40 mg", route="Oral", frequency="OD", start_date=timezone.localdate())
        given = MARAdministration.objects.create(mar=order, scheduled_time=timezone.now() - timedelta(hours=2),
                                                 status=MARAdministration.ADMINISTERED)
        MARAdministration.objects.create(mar=order, scheduled_time=timezone.now() + timedelta(minutes=30))

        response = self.client.post(self.url("complete_discharge"), **self.as_user(self.doctor_user))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertFalse(order.is_active)
        self.assertIsNotNone(order.end_date)
        given.refresh_from_db()
        self.assertEqual(given.status, MARAdministration.ADMINISTERED)  # history kept
        due = MARAdministration.objects.filter(mar__is_active=True, status=MARAdministration.SCHEDULED,
                                               mar__admission=self.admission)
        self.assertFalse(due.exists())

    def test_final_bill_charges_bed_days_plus_extra_lines(self):
        response = self.client.post(
            self.url("final_bill"),
            {"items": [{"description": "Medicines", "quantity": 1, "unit_price": "450.50"}]},
            format="json",
            **self.as_user(self.billing_user),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        invoice = Invoice.objects.get(pk=response.data["id"])
        self.assertEqual(invoice.admission, self.admission)
        self.assertEqual(invoice.total_amount, Decimal("3450.50"))
        self.assertTrue(invoice.is_final)
        self.assertEqual(list(invoice.items.values_list("description", flat=True)),
                         ["Bed charges (general, ₹1000.00/day): 3 day(s)", "Medicines"])

    def test_only_one_live_final_bill_per_stay(self):
        header = self.as_user(self.billing_user)
        first = self.client.post(self.url("final_bill"), {}, format="json", **header)
        second = self.client.post(self.url("final_bill"), {}, format="json", **header)
        Invoice.objects.filter(pk=first.data["id"]).update(status=Invoice.Status.CANCELLED)
        replacement = self.client.post(self.url("final_bill"), {}, format="json", **header)

        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(replacement.status_code, status.HTTP_201_CREATED, replacement.data)
        self.assertEqual(Invoice.objects.get(pk=replacement.data["id"]).total, Decimal("3000.00"))

    def test_final_bill_rejects_bad_amounts(self):
        header = self.as_user(self.billing_user)
        for rate in ("-5", "abc", "NaN"):
            response = self.client.post(self.url("final_bill"), {"daily_rate": rate}, format="json", **header)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, rate)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_bill_needs_discharge_started(self):
        Admission.objects.filter(pk=self.admission.pk).update(status="Admitted")

        response = self.client.post(self.url("final_bill"), {}, format="json", **self.as_user(self.billing_user))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nurse_cannot_create_the_bill_and_billing_sees_only_the_brief(self):
        nurse = staff("nurse", self.hospital, StaffRole.NURSE)
        refused = self.client.post(self.url("final_bill"), {}, format="json", **self.as_user(nurse))

        listed = self.client.get(self.url("awaiting_final_bill", detail=False), **self.as_user(self.billing_user))
        admission_read = self.client.get(f"/api/ipd/admissions/{self.admission.pk}/", **self.as_user(self.billing_user))

        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data[0]["patient_name"], "Asha")
        self.assertNotIn("reason", listed.data[0])
        self.assertEqual(admission_read.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_hospitals_billing_cannot_bill_this_stay(self):
        outsider = staff("bill_b", self.other_hospital, StaffRole.BILLING_STAFF)
        self.client.force_authenticate(user=outsider)

        response = self.client.post(
            self.url("final_bill"), {}, format="json", HTTP_X_HOSPITAL_ID=str(self.other_hospital.pk)
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Invoice.objects.count(), 0)
