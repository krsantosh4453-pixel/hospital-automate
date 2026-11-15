"""Dashboard statistics endpoints (synthetic data only)."""

from datetime import time, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from config.hospital_time import hospital_today

from appointments.models import Appointment
from doctors.models import Doctor
from encounters.models import QueueToken, Visit
from hospital.models import Hospital
from laboratory.models import LabTest
from patients.models import Patient
from users.models import StaffRole

from .test_tenant_isolation import make_staff


class HomeStatsTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Stats Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        self.user, _ = make_staff("stats_admin", self.hospital)
        Patient.objects.create(name="Synthetic Stats Patient", age=40, gender="Male", phone="9000000077", hospital=self.hospital)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)

    def test_summary_endpoint_returns_counts(self):
        # Regression: this view used Sum without importing it (NameError -> 500).
        response = self.client.get(f"/api/home/stats/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["patients"], 1)
        self.assertEqual(response.data["total_revenue"], 0.0)

    def test_detail_endpoint_used_by_dashboard(self):
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["statistics"]["patients"]["total"], 1)
        self.assertEqual(response.data["recent_patients"][0]["name"], "Synthetic Stats Patient")

    def test_lab_count_uses_the_test_hospital_not_the_patient_registration(self):
        # R-07: a shared patient's tests at another hospital are not this hospital's.
        patient = Patient.objects.get(hospital=self.hospital)
        LabTest.objects.create(name="Synthetic CBC here", patient=patient, hospital=self.hospital)
        LabTest.objects.create(name="Synthetic CBC elsewhere", patient=patient, hospital=self.other)
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["statistics"]["laboratory"]["total"], 1)

    def test_lab_counts_follow_the_real_test_statuses(self):
        # R-16: pending/completed/urgent once filtered on statuses a LabTest never has.
        patient = Patient.objects.get(hospital=self.hospital)
        for status in ("Ordered", "Processing", "Result Entered", "Verified", "Released", "Cancelled"):
            LabTest.objects.create(name=f"Synthetic {status}", patient=patient, hospital=self.hospital, status=status)
        LabTest.objects.create(name="Synthetic urgent", patient=patient, hospital=self.hospital,
                               status="Collected", priority="Urgent")
        LabTest.objects.create(name="Synthetic urgent done", patient=patient, hospital=self.hospital,
                               status="Released", priority="Urgent")
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        lab = response.data["statistics"]["laboratory"]
        self.assertEqual(lab["total"], 8)
        self.assertEqual(lab["pending"], 4)  # Ordered, Processing, Result Entered, Collected
        self.assertEqual(lab["completed"], 3)  # Verified, Released, urgent Released
        self.assertEqual(lab["urgent"], 1)

    def test_active_doctors_are_the_available_ones(self):
        # R-17: this counted status="Active", which a doctor never has, so it was always 0.
        Doctor.objects.create(hospital=self.hospital, name="Dr Available", specialization="", phone="")
        Doctor.objects.create(hospital=self.hospital, name="Dr Away", status="On Leave", specialization="", phone="")
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        doctors = response.data["statistics"]["doctors"]
        self.assertEqual(doctors["total"], 2)
        self.assertEqual(doctors["active"], 1)

    def test_other_hospital_is_refused(self):
        for url in ("/api/home/stats/", "/api/home/stats/detail/"):
            response = self.client.get(f"{url}?hospital={self.other.id}")
            self.assertEqual(response.status_code, 403, url)


class DoctorHomeStatsTests(TestCase):
    """A Doctor's home counts cover only the patients in their own care."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Doctor Stats", is_active=True)
        self.doctor_user, _ = make_staff("stats_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.admin_user, _ = make_staff("stats_admin_2", self.hospital)
        colleague_user, _ = make_staff("stats_colleague", self.hospital, role=StaffRole.DOCTOR)
        doctor = Doctor.objects.create(hospital=self.hospital, user=self.doctor_user, name="Dr Own",
                                       specialization="General", phone="9000000901")
        colleague = Doctor.objects.create(hospital=self.hospital, user=colleague_user, name="Dr Else",
                                          specialization="General", phone="9000000902")
        today = hospital_today()  # the dashboard counts the hospital's day
        for name, phone, who in (("Synthetic Own", "9000000903", doctor), ("Synthetic Else", "9000000904", colleague)):
            patient = Patient.objects.create(name=name, age=40, gender="Male", phone=phone, hospital=self.hospital)
            Appointment.objects.create(hospital=self.hospital, patient=patient, doctor=who,
                                       appointment_date=today, appointment_time=time(10, 0), status="Scheduled")

    def stats(self, user, url="/api/home/stats/detail/"):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        response = client.get(f"{url}?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.data

    def test_doctor_dashboard_counts_only_their_patients(self):
        data = self.stats(self.doctor_user)
        stats = data["statistics"]
        self.assertEqual(stats["patients"]["total"], 1)
        self.assertEqual(stats["appointments"]["today"], 1)
        self.assertEqual(stats["appointments"]["pending"], 1)
        self.assertEqual([p["name"] for p in data["recent_patients"]], ["Synthetic Own"])

    def test_doctor_summary_counts_only_their_patients(self):
        data = self.stats(self.doctor_user, "/api/home/stats/")
        self.assertEqual(data["patients"], 1)
        self.assertEqual(data["today_appointments"], 1)

    def test_admin_still_counts_the_whole_hospital(self):
        stats = self.stats(self.admin_user)["statistics"]
        self.assertEqual(stats["patients"]["total"], 2)
        self.assertEqual(stats["appointments"]["today"], 2)


class QueueStatsAreForTodayTests(TestCase):
    """The queue counts match the queue board, which shows only today's tokens."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Queue Stats", is_active=True)
        self.user, _ = make_staff("queue_stats_admin", self.hospital)
        doctor = Doctor.objects.create(hospital=self.hospital, name="Dr Queue", specialization="", phone="")
        patient = Patient.objects.create(name="Synthetic Queue Patient", age=40, gender="Male",
                                         phone="9000000955", hospital=self.hospital)
        today = hospital_today()
        yesterday = today - timedelta(days=1)
        tokens = (
            (1, yesterday, QueueToken.Status.WAITING),
            (2, yesterday, QueueToken.Status.IN_CONSULTATION),
            (3, yesterday, QueueToken.Status.COMPLETED),
            (1, today, QueueToken.Status.WAITING),
        )
        for number, day, status in tokens:
            visit = Visit.objects.create(patient=patient, doctor=doctor, hospital=self.hospital)
            QueueToken.objects.create(visit=visit, hospital=self.hospital, patient=patient, doctor=doctor,
                                      token_number=number, token_date=day, status=status)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)

    def test_dashboard_queue_counts_ignore_earlier_days(self):
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        queue = response.data["statistics"]["queue"]
        self.assertEqual(queue["total"], 1)
        self.assertEqual(queue["waiting"], 1)
        self.assertEqual(queue["in_consultation"], 0)
        self.assertEqual(queue["completed"], 0)

    def test_summary_waiting_count_ignores_earlier_days(self):
        response = self.client.get(f"/api/home/stats/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["waiting_queue"], 1)


class BillingStatsTests(TestCase):
    """The dashboard's billing figures follow the real invoice statuses and count refunds as money paid back."""

    def setUp(self):
        from billing.models import Invoice, InvoiceItem
        from billing.services import recalculate, record_payment, record_refund

        self.hospital = Hospital.objects.create(name="Synthetic Billing Stats", is_active=True)
        self.admin, _ = make_staff("billing_stats_admin", self.hospital)
        self.lab_staff, _ = make_staff("billing_stats_lab", self.hospital, role=StaffRole.LAB_STAFF)
        patient = Patient.objects.create(name="Synthetic Billing Patient", age=40, gender="Male",
                                         phone="9000000966", hospital=self.hospital)

        def bill(number, amount):
            invoice = Invoice.objects.create(patient=patient, hospital=self.hospital, invoice_number=number)
            InvoiceItem.objects.create(invoice=invoice, description="Synthetic consultation",
                                       quantity=1, unit_price=amount, subtotal=amount)
            return recalculate(invoice)

        unpaid = bill("SYN-1", 1000)
        partial = bill("SYN-2", 1000)
        paid = bill("SYN-3", 500)
        record_payment(partial, 400, method="UPI")
        record_payment(paid, 500, method="Cash")
        record_refund(paid, 100, "Synthetic overcharge")  # paid becomes Partially Paid again
        cancelled = bill("SYN-4", 300)
        cancelled.status = Invoice.Status.CANCELLED
        cancelled.save(update_fields=["status"])
        self.unpaid, self.partial, self.paid = unpaid, partial, paid

    def billing(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        response = client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.data["statistics"]["billing"]

    def test_partially_paid_invoices_are_counted(self):
        billing = self.billing(self.admin)
        self.assertEqual(billing["total_invoices"], 4)
        self.assertEqual(billing["pending"], 1)
        self.assertEqual(billing["partial"], 2)  # SYN-2, and SYN-3 after its refund
        self.assertEqual(billing["paid"], 0)

    def test_revenue_is_net_of_refunds(self):
        billing = self.billing(self.admin)
        self.assertEqual(billing["total_revenue"], 800.0)  # 400 + 500 - 100
        self.assertEqual(billing["today_revenue"], 800.0)
        self.assertEqual(billing["refunded"], 100.0)
        summary = APIClient(raise_request_exception=False)
        summary.force_authenticate(self.admin)
        self.assertEqual(summary.get(f"/api/home/stats/?hospital={self.hospital.id}").data["total_revenue"], 800.0)

    def test_outstanding_is_what_open_bills_still_owe(self):
        # 1000 unpaid + 600 left on SYN-2 + 100 left on SYN-3; the cancelled bill owes nothing.
        self.assertEqual(self.billing(self.admin)["outstanding"], 1700.0)

    def test_money_figures_stay_hidden_from_roles_without_revenue_access(self):
        billing = self.billing(self.lab_staff)
        self.assertEqual(billing["partial"], 2)
        for key in ("total_revenue", "today_revenue", "refunded", "outstanding"):
            self.assertIsNone(billing[key], key)
