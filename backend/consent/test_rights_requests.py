"""P1-03: DPDP Act data-principal requests and the privacy notice (synthetic data)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditLog
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

User = get_user_model()
URL = "/api/consent/rights-requests/"


@override_settings(DPDP_RESPONSE_DAYS=30)
class RightsRequestTests(TestCase):
    def setUp(self):
        self.a = Hospital.objects.create(name="Synthetic Rights A", is_active=True,
                                         grievance_officer_name="Synthetic Officer",
                                         grievance_officer_email="privacy@example.test",
                                         grievance_officer_phone="9000000080")
        self.b = Hospital.objects.create(name="Synthetic Rights B", is_active=True)
        self.admin_a, _ = make_staff("rights_admin_a", self.a, role=StaffRole.ADMIN)
        self.admin_b, _ = make_staff("rights_admin_b", self.b, role=StaffRole.ADMIN)
        self.desk_a, _ = make_staff("rights_desk_a", self.a, role=StaffRole.RECEPTIONIST)
        self.login = User.objects.create_user(username="rights_patient", password="Synthetic-Pass-123")
        self.patient = Patient.objects.create(name="Synthetic Principal", age=50, gender="Female",
                                              phone="9000000081", hospital=self.a, user=self.login)
        PatientHospital.objects.create(patient=self.patient, hospital=self.a, uhid="RA-1")
        other_login = User.objects.create_user(username="rights_other", password="Synthetic-Pass-123")
        self.other = Patient.objects.create(name="Synthetic Other", age=40, gender="Male",
                                            phone="9000000082", hospital=self.a, user=other_login)
        self.other_login = other_login

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        if hospital is not None:
            client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def file(self, kind="erasure", hospital=None, user=None):
        return self.client_for(user or self.login).post(URL, {
            "hospital": (hospital or self.a).id, "kind": kind, "details": "Please delete my phone number.",
        }, format="json")

    # --- the patient --------------------------------------------------------

    def test_patient_files_a_request_with_a_due_date_and_it_is_audited(self):
        resp = self.file()

        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body["kind"], body["status"]), ("erasure", "received"))
        due = timezone.datetime.fromisoformat(body["due_at"].replace("Z", "+00:00"))
        self.assertAlmostEqual((due - timezone.now()).days, 29, delta=1)
        self.assertTrue(AuditLog.objects.filter(action="consent.rights_request.create").exists())

    def test_patient_cannot_file_at_a_hospital_they_are_not_registered_at(self):
        self.assertEqual(self.file(hospital=self.b).status_code, 400)

    def test_unknown_kind_is_refused(self):
        self.assertEqual(self.file(kind="sell_my_data").status_code, 400)

    def test_patient_sees_only_their_own_requests(self):
        self.file()
        self.file(user=self.other_login)

        rows = self.client_for(self.login).get(URL).json()["results"]

        self.assertEqual([row["patient"] for row in rows], [self.patient.pk])

    # --- the hospital -------------------------------------------------------

    def test_admin_sees_their_hospitals_requests_only(self):
        self.file()

        self.assertEqual(len(self.client_for(self.admin_a, self.a).get(URL).json()["results"]), 1)
        self.assertEqual(self.client_for(self.admin_b, self.b).get(URL).json()["results"], [])

    def test_only_admin_or_manager_answers(self):
        request_id = self.file().json()["id"]

        resp = self.client_for(self.desk_a, self.a).post(f"{URL}{request_id}/respond/",
                                                         {"status": "completed", "response": "Done and noted."},
                                                         format="json")

        self.assertEqual(resp.status_code, 403)

    def test_closing_needs_a_written_reason_and_is_audited(self):
        request_id = self.file().json()["id"]
        admin = self.client_for(self.admin_a, self.a)

        self.assertEqual(admin.post(f"{URL}{request_id}/respond/", {"status": "refused"}, format="json").status_code, 400)
        resp = admin.post(f"{URL}{request_id}/respond/", {
            "status": "refused", "response": "Medical records must be kept for three years; phone number removed instead.",
        }, format="json")

        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "refused")
        self.assertIsNotNone(resp.json()["closed_at"])
        self.assertTrue(AuditLog.objects.filter(action="consent.rights_request.respond").exists())

    def test_admin_of_another_hospital_cannot_answer(self):
        request_id = self.file().json()["id"]

        resp = self.client_for(self.admin_b, self.b).post(f"{URL}{request_id}/respond/",
                                                          {"status": "completed", "response": "Not my hospital."},
                                                          format="json")

        self.assertEqual(resp.status_code, 404)

    def test_open_requests_past_their_due_date_are_marked_overdue(self):
        request_id = self.file().json()["id"]
        from consent.models import DataRightsRequest

        DataRightsRequest.objects.filter(pk=request_id).update(due_at=timezone.now() - timedelta(days=1))

        row = self.client_for(self.admin_a, self.a).get(URL).json()["results"][0]
        self.assertTrue(row["overdue"])

    # --- notice -------------------------------------------------------------

    def test_privacy_notice_names_the_grievance_officer(self):
        resp = self.client_for(self.login).get("/api/consent/privacy-notice/", {"hospital": self.a.id})

        self.assertEqual(resp.status_code, 200, resp.content)
        officer = resp.json()["grievance_officer"]
        self.assertEqual((officer["name"], officer["email"]), ("Synthetic Officer", "privacy@example.test"))
        self.assertEqual(resp.json()["response_days"], 30)
