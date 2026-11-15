"""
Phase 3: cross-hospital tests for the hand-written views ("own-checks" in
config/tenancy_exemptions.py), which the generic probe cannot route.

The caller is Hospital A's Admin. Every record below belongs to Hospital B
(synthetic data). A view passes when B's record is refused (403/404) or left
out of the list, under both /api/ and /api/v1/ and with a forged
X-Hospital-ID: B, and no write to it succeeds.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from patients.models import Patient, PatientHospital

from .factory import SyntheticFactory
from .test_tenant_isolation import HospitalBRecords, _ids

User = get_user_model()
PREFIXES = ("/api/", "/api/v1/")


class HandwrittenViewsIsolationTests(HospitalBRecords, TestCase):
    def client_as(self, user, hospital):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def callers(self):
        """A's Admin acting in A, and the same login forging X-Hospital-ID: B."""
        return (self.client_as(self.user_a, self.hospital_a), self.client_as(self.user_a, self.hospital_b))

    def b(self, label):
        return self.b_records[label]

    def assert_hidden(self, path, pk, method="get", data=None):
        for prefix in PREFIXES:
            for client in self.callers():
                response = getattr(client, method)(prefix + path, data or {}, format="json")
                where = f"{method.upper()} {prefix}{path} ({response.status_code})"
                self.assertLess(response.status_code, 500, where)
                if response.status_code in (200, 201):
                    self.assertEqual(method, "get", f"write succeeded: {where}")
                    self.assertNotIn(pk, _ids(response.json()), f"B's record visible: {where}")
                    self.assertNotEqual(response.json().get("id") if isinstance(response.json(), dict) else None,
                                        pk, f"B's record returned: {where}")

    def assert_refused(self, path, method="get", data=None, query=""):
        for prefix in PREFIXES:
            for client in self.callers():
                response = getattr(client, method)(prefix + path + query, data or {}, format="json")
                self.assertIn(response.status_code, (400, 403, 404),
                              f"{method.upper()} {prefix}{path}{query} -> {response.status_code}")

    # Consent and record sharing -------------------------------------------

    def test_consent_records(self):
        record = self.b("consent.ConsentRecord")
        self.assert_hidden("consent/records/", record.pk)
        self.assert_refused(f"consent/records/{record.pk}/")
        self.assert_refused(f"consent/records/{record.pk}/revoke/", method="post")

    def test_record_shares(self):
        share = self.b("consent.RecordShare")
        self.assert_hidden("consent/shares/", share.pk)
        self.assert_hidden("consent/shares/received/", share.pk)
        self.assert_refused(f"consent/shares/{share.pk}/access-log/")
        self.assert_refused(f"consent/shares/{share.pk}/records/")
        self.assert_refused(f"consent/shares/{share.pk}/revoke/", method="post")

    def test_data_rights_requests(self):
        request = self.b("consent.DataRightsRequest")
        self.assert_hidden("consent/rights-requests/", request.pk)
        self.assert_refused(f"consent/rights-requests/{request.pk}/respond/", method="post",
                            data={"status": "Completed", "response": "x"})

    # Documents -------------------------------------------------------------

    def test_documents(self):
        document = self.b("patients.PatientDocument")
        self.assert_hidden("documents/", document.pk)
        self.assert_hidden("documents/search/?q=S", document.pk)
        for suffix in ("", "download/", "preview/"):
            self.assert_refused(f"documents/{document.pk}/{suffix}")

    def test_documents_of_a_patient_shared_by_both_hospitals(self):
        # The patient is registered at A and B; A sees only its own documents of them.
        document = self.b("patients.PatientDocument")
        self.assertEqual(document.patient_id, self.shared_patient.pk)
        self.assert_hidden(f"documents/patient/{self.shared_patient.pk}/", document.pk)

    def test_uploading_into_hospital_b_is_refused(self):
        forged = self.client_as(self.user_a, self.hospital_b)
        for prefix in PREFIXES:
            response = forged.post(f"{prefix}documents/patient/{self.shared_patient.pk}/upload/", {"title": "x"})
            self.assertIn(response.status_code, (400, 403, 404), prefix)

    # Reports ----------------------------------------------------------------

    def test_saved_scheduled_reports_and_snapshots(self):
        for label, path in (("reports.SavedReport", "reports/saved/"), ("reports.ScheduledReport", "reports/scheduled/"),
                            ("reports.KPISnapshot", "reports/snapshots/")):
            record = self.b(label)
            self.assert_hidden(path, record.pk)
            self.assert_refused(f"{path}{record.pk}/")

    def test_analytics_for_hospital_b_are_refused(self):
        client = self.client_as(self.user_a, self.hospital_a)
        for prefix in PREFIXES:
            response = client.get(f"{prefix}reports/analytics/ai-scribe/?hospital={self.hospital_b.id}")
            self.assertIn(response.status_code, (400, 403, 404), prefix)

    # Staff administration --------------------------------------------------

    def test_staff_administration_of_hospital_b_is_refused(self):
        forged = self.client_as(self.user_a, self.hospital_b)
        client = self.client_as(self.user_a, self.hospital_a)
        for prefix in PREFIXES:
            self.assertEqual(forged.get(f"{prefix}users/").status_code, 403, prefix)
            self.assertIn(client.patch(f"{prefix}users/{self.user_b.id}/membership/", {"is_active": False},
                                       format="json").status_code, (403, 404), prefix)
            self.assertIn(client.post(f"{prefix}users/{self.user_b.id}/invite/").status_code, (403, 404), prefix)
        self.assertTrue(self.user_b.staff_profile.hospital_memberships.get(hospital=self.hospital_b).is_active)

    def test_staff_list_shows_only_the_acting_hospital(self):
        client = self.client_as(self.user_a, self.hospital_a)
        for prefix in PREFIXES:
            body = client.get(f"{prefix}users/").json()
            self.assertNotIn(self.user_b.id, _ids(body.get("staff", body)), prefix)

    def test_inviting_into_hospital_b_is_refused(self):
        forged = self.client_as(self.user_a, self.hospital_b)
        for prefix in PREFIXES:
            response = forged.post(f"{prefix}users/invite/", {"name": "X", "email": "x@example.test",
                                                              "role": "Receptionist"}, format="json")
            self.assertEqual(response.status_code, 403, prefix)

    # Dashboards, break-glass, ABDM and FHIR --------------------------------

    def test_home_dashboard_for_hospital_b_is_refused(self):
        client = self.client_as(self.user_a, self.hospital_a)
        for prefix in PREFIXES:
            for path in ("home/", "home/stats/"):
                response = client.get(f"{prefix}{path}?hospital={self.hospital_b.id}")
                self.assertIn(response.status_code, (400, 403, 404), f"{prefix}{path}")

    def test_break_glass_grants(self):
        grant = self.b("audit.BreakGlassAccess")
        self.assert_hidden("audit/break-glass/", grant.pk)
        self.assert_refused(f"audit/break-glass/{grant.pk}/")

    def test_abdm_and_fhir_refuse_hospital_b(self):
        forged = self.client_as(self.user_a, self.hospital_b)
        for prefix in PREFIXES:
            for path in ("abdm/status/", "abdm/abha/links/", "fhir/Patient", f"fhir/Patient/{self.shared_patient.pk}"):
                self.assertIn(forged.get(f"{prefix}{path}").status_code, (403, 404), f"{prefix}{path}")


class PatientCrossHospitalTests(TestCase):
    """A patient of Hospital A cannot reach another patient's records at Hospital B."""

    @classmethod
    def setUpTestData(cls):
        from hospital.models import Hospital

        cls.hospital_a = Hospital.objects.create(name="Synthetic Patient A", is_active=True)
        cls.hospital_b = Hospital.objects.create(name="Synthetic Patient B", is_active=True)
        cls.login_a = User.objects.create_user(username="cross_patient_a")
        cls.patient_a = Patient.objects.create(user=cls.login_a, name="Synthetic Cross A", age=30, gender="Female",
                                               phone="9000000070", hospital=cls.hospital_a)
        PatientHospital.objects.create(patient=cls.patient_a, hospital=cls.hospital_a, uhid="CRA-1")
        cls.patient_b = Patient.objects.create(name="Synthetic Cross B", age=31, gender="Male",
                                               phone="9000000071", hospital=cls.hospital_b)
        PatientHospital.objects.create(patient=cls.patient_b, hospital=cls.hospital_b, uhid="CRB-1")
        factory = SyntheticFactory(fixed={"hospital.Hospital": cls.hospital_b, "patients.Patient": cls.patient_b})
        from django.apps import apps

        cls.b_rows = {label: factory.get(apps.get_model(label)) for label in (
            "appointments.Appointment", "clinical.Prescription", "billing.Invoice", "patients.PatientDocument")}

    def test_patient_a_cannot_read_patient_bs_records(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.login_a)
        for label, path in (("appointments.Appointment", "appointments/"), ("clinical.Prescription", "clinical/prescriptions/"),
                            ("billing.Invoice", "billing/invoices/")):
            row = self.b_rows[label]
            for prefix in PREFIXES:
                listing = client.get(f"{prefix}{path}?patient={self.patient_b.pk}")
                self.assertLess(listing.status_code, 500, path)
                if listing.status_code == 200:
                    self.assertNotIn(row.pk, _ids(listing.json()), f"{prefix}{path}")
                self.assertIn(client.get(f"{prefix}{path}{row.pk}/").status_code, (403, 404), f"{prefix}{path}")
        for prefix in PREFIXES:
            self.assertIn(client.get(f"{prefix}documents/patient/{self.patient_b.pk}/").status_code, (403, 404))
            self.assertIn(client.get(f"{prefix}documents/{self.b_rows['patients.PatientDocument'].pk}/").status_code,
                          (403, 404))
