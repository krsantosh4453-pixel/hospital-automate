"""
R-15: reads of consent records, record shares, patient documents, analytics
and revenue are limited by role, not only by hospital membership.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from consent.models import ConsentRecord, RecordShare
from hospital.models import Hospital
from patients.models import Patient, PatientDocument
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_in_care


class ReadRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Read Roles", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Read Roles Peer", is_active=True)
        cls.admin, _ = make_staff("rr_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.reception, _ = make_staff("rr_reception", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.billing, _ = make_staff("rr_billing", cls.hospital, role=StaffRole.BILLING_STAFF)
        cls.pharmacist, _ = make_staff("rr_pharmacist", cls.hospital, role=StaffRole.PHARMACIST)
        cls.lab, _ = make_staff("rr_lab", cls.hospital, role=StaffRole.LAB_STAFF)
        cls.nurse, _ = make_staff("rr_nurse", cls.hospital, role=StaffRole.NURSE)
        cls.doctor, _ = make_staff("rr_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.pharmacist_other, _ = make_staff("rr_pharmacist_b", cls.other, role=StaffRole.PHARMACIST)

        cls.mine = Patient.objects.create(name="Synthetic In Care", age=40, gender="Male",
                                          phone="9000000401", hospital=cls.hospital)
        cls.theirs = Patient.objects.create(name="Synthetic Not In Care", age=41, gender="Female",
                                            phone="9000000402", hospital=cls.hospital)
        put_in_care(cls.doctor, cls.hospital, cls.mine)

        consent = {"hospital": cls.hospital, "form_code": "general-treatment", "form_version": "1.0",
                   "recorded_by": cls.reception}
        cls.consent_mine = ConsentRecord.objects.create(patient=cls.mine, signed_name="Synthetic In Care", **consent)
        cls.consent_theirs = ConsentRecord.objects.create(
            patient=cls.theirs, signed_name="Synthetic Not In Care", **consent)
        cls.share = RecordShare.objects.create(
            patient=cls.theirs, source_hospital=cls.other, recipient_hospital=cls.hospital,
            scope=["diagnoses"], purpose="Second opinion", expires_at=timezone.now() + timedelta(days=7),
        )
        cls.doc_mine = PatientDocument.objects.create(
            patient=cls.mine, hospital=cls.hospital, title="Synthetic scan", folder="imaging", file="")
        cls.doc_theirs = PatientDocument.objects.create(
            patient=cls.theirs, hospital=cls.hospital, title="Synthetic report", folder="lab", file="")

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    # Consent

    def test_non_consent_roles_cannot_list_consents_or_shares(self):
        for user in (self.pharmacist, self.lab, self.billing):
            client = self.client_for(user)
            with self.subTest(user=user.username):
                self.assertEqual(client.get("/api/consent/records/").status_code, 403)
                self.assertEqual(client.get(f"/api/consent/records/{self.consent_mine.id}/").status_code, 403)
                self.assertEqual(client.get("/api/consent/shares/").status_code, 403)
                self.assertEqual(client.get("/api/consent/shares/received/").status_code, 403)

    def test_front_desk_reads_every_consent_of_the_hospital(self):
        rows = self.client_for(self.reception).get("/api/consent/records/").json()["results"]
        self.assertEqual({r["id"] for r in rows}, {self.consent_mine.id, self.consent_theirs.id})
        received = self.client_for(self.reception).get("/api/consent/shares/received/").json()["results"]
        self.assertEqual([s["id"] for s in received], [self.share.id])

    def test_doctor_reads_consents_of_patients_in_their_care_only(self):
        client = self.client_for(self.doctor)
        rows = client.get("/api/consent/records/").json()["results"]
        self.assertEqual([r["id"] for r in rows], [self.consent_mine.id])
        self.assertEqual(client.get(f"/api/consent/records/{self.consent_theirs.id}/").status_code, 404)
        self.assertEqual(client.get(f"/api/consent/records/{self.consent_mine.id}/").status_code, 200)

    # Documents

    def test_non_document_roles_cannot_read_documents(self):
        for user in (self.pharmacist, self.billing):
            client = self.client_for(user)
            with self.subTest(user=user.username):
                self.assertEqual(client.get("/api/documents/").status_code, 403)
                self.assertEqual(client.get(f"/api/documents/{self.doc_mine.id}/").status_code, 403)
                self.assertEqual(client.get("/api/documents/search/?q=Synthetic").status_code, 403)
                self.assertEqual(client.get(f"/api/documents/patient/{self.mine.id}/").status_code, 403)

    def test_document_roles_read_the_hospital_documents(self):
        for user in (self.admin, self.reception, self.lab):
            with self.subTest(user=user.username):
                body = self.client_for(user).get("/api/documents/").json()
                self.assertEqual(body["count"], 2)

    def test_doctor_reads_documents_of_patients_in_their_care_only(self):
        client = self.client_for(self.doctor)
        listed = client.get("/api/documents/").json()["documents"]
        self.assertEqual([d["id"] for d in listed], [self.doc_mine.id])
        self.assertEqual(client.get(f"/api/documents/{self.doc_theirs.id}/").status_code, 404)

    def test_staff_of_another_hospital_still_cannot_read(self):
        client = self.client_for(self.pharmacist_other, self.hospital)
        self.assertEqual(client.get("/api/documents/").status_code, 403)
        self.assertEqual(client.get("/api/consent/records/").status_code, 403)

    # Analytics and revenue

    def dashboard(self, user):
        return self.client_for(user).get(f"/api/reports/analytics/dashboard/?hospital={self.hospital.id}")

    def test_dashboard_hides_money_from_roles_that_do_not_handle_it(self):
        for user in (self.nurse, self.doctor, self.pharmacist, self.lab):
            with self.subTest(user=user.username):
                resp = self.dashboard(user)
                self.assertEqual(resp.status_code, 200, resp.content)
                body = resp.json()
                self.assertIsNone(body["billing"]["period_revenue"])
                self.assertIsNone(body["billing"]["daily_revenue"])
                self.assertIsNone(body["pharmacy"]["period_revenue"])
                # Counts stay visible.
                self.assertIn("period_invoices", body["billing"])

    def test_dashboard_shows_money_to_finance_roles(self):
        for user in (self.admin, self.billing, self.reception):
            with self.subTest(user=user.username):
                body = self.dashboard(user).json()
                self.assertEqual(body["billing"]["period_revenue"], 0.0)
                self.assertEqual(body["pharmacy"]["period_revenue"], 0.0)

    def test_revenue_reports_are_refused_to_other_roles(self):
        query = f"?hospital={self.hospital.id}"
        for path in ("financial", "billing", "forecast/revenue"):
            with self.subTest(path=path):
                url = f"/api/reports/analytics/{path}/{query}"
                self.assertEqual(self.client_for(self.nurse).get(url).status_code, 403)
                self.assertEqual(self.client_for(self.billing).get(url).status_code, 200)

    def test_pharmacy_report_and_forecasts_drop_money_for_other_roles(self):
        query = f"?hospital={self.hospital.id}"
        pharmacy = self.client_for(self.lab).get(f"/api/reports/analytics/pharmacy/{query}").json()
        self.assertIsNone(pharmacy["period_revenue"])
        forecasts = self.client_for(self.lab).get(f"/api/reports/analytics/forecast/{query}").json()
        self.assertNotIn("revenue", forecasts)
        self.assertIn("appointments", forecasts)
        admin_forecasts = self.client_for(self.admin).get(f"/api/reports/analytics/forecast/{query}").json()
        self.assertIn("revenue", admin_forecasts)

    def test_home_revenue_only_for_finance_roles(self):
        query = f"?hospital={self.hospital.id}"
        for user, visible in ((self.reception, True), (self.billing, True), (self.nurse, False), (self.lab, False)):
            with self.subTest(user=user.username):
                client = self.client_for(user)
                billing = client.get(f"/api/home/{query}").json()["statistics"]["billing"]
                summary = client.get(f"/api/home/stats/{query}").json()
                if visible:
                    self.assertEqual(billing["today_revenue"], 0.0)
                    self.assertEqual(summary["total_revenue"], 0.0)
                else:
                    self.assertIsNone(billing["today_revenue"])
                    self.assertIsNone(billing["total_revenue"])
                    self.assertIsNone(summary["total_revenue"])
