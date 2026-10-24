"""Patient documents: per-hospital access, audited reads, content validation."""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from audit.models import AuditLog
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

User = get_user_model()
MEDIA = tempfile.mkdtemp(prefix="hms-doc-test-")
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@override_settings(MEDIA_ROOT=MEDIA)
class DocumentAccessTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.a = Hospital.objects.create(name="Synthetic Doc A", is_active=True)
        self.b = Hospital.objects.create(name="Synthetic Doc B", is_active=True)
        self.doc_a, _ = make_staff("doc_staff_a", self.a, role=StaffRole.DOCTOR)
        self.doc_b, _ = make_staff("doc_staff_b", self.b, role=StaffRole.DOCTOR)
        self.login = User.objects.create_user(username="doc_patient", password="Synthetic-Pass-123")
        self.patient = Patient.objects.create(name="Synthetic Doc Patient", age=40, gender="Male",
                                              phone="9000000050", hospital=self.a, user=self.login)
        PatientHospital.objects.create(patient=self.patient, hospital=self.a, uhid="DA-1")
        PatientHospital.objects.create(patient=self.patient, hospital=self.b, uhid="DB-1")

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        if hospital:
            client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def upload(self, user, hospital, content=PDF, name="report.pdf"):
        return self.client_for(user, hospital).post(
            f"/api/documents/patient/{self.patient.id}/upload/",
            {"file": SimpleUploadedFile(name, content), "title": "Synthetic report", "folder": "lab"},
            format="multipart",
        )

    def test_hospital_scoped_download_and_audit(self):
        resp = self.upload(self.doc_b, self.b)
        self.assertEqual(resp.status_code, 201, resp.content)
        doc_id = resp.json()["id"]

        # Hospital A shares the patient but not this hospital-B document.
        self.assertEqual(self.client_for(self.doc_a, self.a).get(f"/api/documents/{doc_id}/download/").status_code, 404)
        listing = self.client_for(self.doc_a, self.a).get(f"/api/documents/patient/{self.patient.id}/").json()
        self.assertEqual(listing["count"], 0)

        ok = self.client_for(self.doc_b, self.b).get(f"/api/documents/{doc_id}/download/")
        self.assertEqual(ok.status_code, 200)
        self.assertIn("attachment", ok["Content-Disposition"])
        self.assertTrue(AuditLog.objects.filter(action="documents.document.download", user=self.doc_b).exists())

        mine = self.client_for(self.login).get(f"/api/documents/{doc_id}/download/")
        self.assertEqual(mine.status_code, 200)

    def test_content_type_is_checked_not_the_name(self):
        resp = self.upload(self.doc_a, self.a, content=b"<html><script>alert(1)</script></html>", name="fake.pdf")
        self.assertEqual(resp.status_code, 400)

    def test_doctor_cannot_delete_and_routes_resolve(self):
        doc_id = self.upload(self.doc_a, self.a).json()["id"]
        self.assertEqual(self.client_for(self.doc_a, self.a).delete(f"/api/documents/{doc_id}/").status_code, 403)
        client = self.client_for(self.doc_a, self.a)
        self.assertEqual(client.get("/api/documents/categories/").status_code, 200)
        self.assertEqual(client.get("/api/documents/search/?q=Synthetic").json()["count"], 1)

    def test_unauthenticated_download_rejected(self):
        doc_id = self.upload(self.doc_a, self.a).json()["id"]
        self.assertEqual(APIClient().get(f"/api/documents/{doc_id}/download/").status_code, 401)
