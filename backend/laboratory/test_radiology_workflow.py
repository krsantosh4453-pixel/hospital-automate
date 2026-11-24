"""
Prompt 5: radiology role (MF-004), imaging attachments (MF-005), imaging
billing (MF-011 / INT-004) and order-visit links (INT-002). Synthetic data only.
"""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from audit.models import AuditLog
from billing.models import InvoiceItem, ServicePrice
from billing.unbilled import charge_unbilled, find_unbilled
from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from laboratory.models import ImagingStudy
from laboratory.test_imaging import URL, rows, staff
from patients.models import Patient, PatientDocument, PatientHospital
from security_tests.test_tenant_isolation import put_in_care
from users.models import StaffRole

# Smallest valid PNG (1x1), so the content check sees a real image.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da6364f8ffbf1e0005fe02fea3c2a1b20000000049454e44ae426082"
)
MEDIA = tempfile.mkdtemp(prefix="hms-radiology-tests-")


@override_settings(MEDIA_ROOT=MEDIA)
class RadiologyFixture(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Imaging A", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Imaging B", is_active=True)
        self.patient = Patient.objects.create(name="Synthetic Scan", age=40, gender="Female", phone="9000055501",
                                              hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="SIA-1", is_active=True)
        self.doctor_user = staff("p5_doc", StaffRole.DOCTOR, (self.hospital, StaffRole.DOCTOR))
        self.doctor = put_in_care(self.doctor_user, self.hospital, self.patient)
        self.visit = Visit.objects.filter(patient=self.patient, hospital=self.hospital).first()
        self.radiologist = staff("p5_rad", StaffRole.DOCTOR, (self.hospital, StaffRole.DOCTOR))
        Doctor.objects.create(user=self.radiologist, hospital=self.hospital, name="Dr Synthetic Rad",
                              specialization="Radiology", phone="9000055502")
        self.radiographer = staff("p5_rgr", StaffRole.RADIOLOGY_STAFF, (self.hospital, StaffRole.RADIOLOGY_STAFF))
        self.lab_tech = staff("p5_lab", StaffRole.LAB_STAFF, (self.hospital, StaffRole.LAB_STAFF))
        self.client = APIClient()

    def call(self, user, method, url, data=None, hospital=None):
        self.client.force_authenticate(user=user)
        header = {"HTTP_X_HOSPITAL_ID": str((hospital or self.hospital).pk)}
        return getattr(self.client, method)(url, data, format="json", **header)

    def order(self, **extra):
        data = {"patient": self.patient.pk, "modality": "X-ray", "body_part": "Chest PA",
                "indication": "Cough 3 weeks", "visit": self.visit.pk}
        data.update(extra)
        response = self.call(self.doctor_user, "post", URL, data)
        self.assertEqual(response.status_code, 201, response.content)
        return response.data["id"]

    def step(self, user, study_id, action, data=None):
        return self.call(user, "post", f"{URL}{study_id}/{action}/", data or {})

    def performed(self):
        study_id = self.order()
        self.assertEqual(self.step(self.radiographer, study_id, "perform").status_code, 200)
        return study_id

    def sign(self, study_id):
        return self.step(self.radiologist, study_id, "report",
                         {"findings": "Clear lung fields.", "impression": "Normal chest."})

    def price(self, applies_to, amount="350.50"):
        return ServicePrice.objects.create(
            hospital=self.hospital, category="imaging", code=f"IMG-{applies_to}"[:40], name=applies_to,
            applies_to=applies_to, unit_price=Decimal(amount), tax_rate=Decimal("0"),
            effective_from=hospital_today() - timedelta(days=30))

    def upload(self, user, study_id, name="chest.png", content=PNG, content_type="image/png"):
        self.client.force_authenticate(user=user)
        return self.client.post(f"{URL}{study_id}/images/", {"file": SimpleUploadedFile(name, content, content_type)},
                                format="multipart", HTTP_X_HOSPITAL_ID=str(self.hospital.pk))


class RadiologyRoleTests(RadiologyFixture):
    def test_radiology_staff_schedule_and_perform_but_never_order_or_sign(self):
        study_id = self.order()

        scheduled = self.step(self.radiographer, study_id, "schedule", {"scheduled_for": "2030-01-01T10:00:00+05:30"})
        performed = self.step(self.radiographer, study_id, "perform")
        ordered = self.call(self.radiographer, "post", URL, {"patient": self.patient.pk, "modality": "X-ray",
                                                             "body_part": "Hand", "indication": "Fall"})
        signed = self.step(self.radiographer, study_id, "report", {"findings": "x", "impression": "y"})

        self.assertEqual((scheduled.status_code, performed.status_code), (200, 200))
        self.assertEqual((ordered.status_code, signed.status_code), (403, 403))
        self.assertEqual(ImagingStudy.objects.get(pk=study_id).performed_by, self.radiographer)

    def test_lab_staff_still_perform_studies_as_before(self):
        study_id = self.order()
        self.assertEqual(self.step(self.lab_tech, study_id, "perform").status_code, 200)

    def test_radiology_staff_cannot_reach_lab_billing_patients_or_pharmacy(self):
        for url in ("/api/laboratory/", "/api/billing/invoices/", "/api/patients/", "/api/pharmacy-sales/",
                    "/api/clinical/vitals/", "/api/nurses/assessments/"):
            with self.subTest(url=url):
                self.assertEqual(self.call(self.radiographer, "get", url).status_code, 403)

    def test_radiology_staff_see_only_their_hospitals_studies(self):
        self.order()
        outsider = staff("p5_rgr_b", StaffRole.RADIOLOGY_STAFF, (self.other, StaffRole.RADIOLOGY_STAFF))

        own = rows(self.call(self.radiographer, "get", URL))
        foreign = self.call(outsider, "get", URL, hospital=self.other)
        forced = self.call(outsider, "get", URL, hospital=self.hospital)

        self.assertEqual(len(own), 1)
        self.assertEqual(rows(foreign), [])
        self.assertEqual(forced.status_code, 403)

    def test_every_step_is_audited_with_who_did_it(self):
        study_id = self.performed()
        self.sign(study_id)
        actions = set(AuditLog.objects.filter(object_id=str(study_id)).values_list("action", "user__username"))
        self.assertIn(("laboratory.imagingstudy.performed", "p5_rgr"), actions)
        self.assertIn(("laboratory.imagingstudy.reported", "p5_rad"), actions)


class ImagingVisitTests(RadiologyFixture):
    def test_an_order_keeps_its_visit_and_ordering_doctor(self):
        study = ImagingStudy.objects.get(pk=self.order())
        self.assertEqual((study.visit_id, study.ordered_by_id), (self.visit.pk, self.doctor.pk))

    def test_a_visit_of_another_patient_is_refused(self):
        stranger = Patient.objects.create(name="Synthetic Other", age=30, gender="Male", phone="9000055509",
                                          hospital=self.hospital)
        PatientHospital.objects.create(patient=stranger, hospital=self.hospital, uhid="SIA-2", is_active=True)
        other_visit = Visit.objects.create(patient=stranger, hospital=self.hospital, doctor=self.doctor)

        response = self.call(self.doctor_user, "post", URL, {
            "patient": self.patient.pk, "modality": "X-ray", "body_part": "Chest PA", "indication": "Cough",
            "visit": other_visit.pk})

        self.assertEqual(response.status_code, 400)
        self.assertIn("visit", str(response.data))

    def test_a_lab_order_with_another_patients_visit_is_refused(self):
        stranger = Patient.objects.create(name="Synthetic Other", age=30, gender="Male", phone="9000055508",
                                          hospital=self.hospital)
        other_visit = Visit.objects.create(patient=stranger, hospital=self.hospital, doctor=self.doctor)

        response = self.call(self.doctor_user, "post", "/api/laboratory/", {
            "patient": self.patient.pk, "name": "CBC", "doctor": self.doctor.pk, "visit": other_visit.pk})

        self.assertEqual(response.status_code, 400)
        self.assertIn("visit", str(response.data))


class ImagingBillingTests(RadiologyFixture):
    def lines(self, study_id):
        return InvoiceItem.objects.filter(charge_key=f"imaging:{study_id}")

    def test_signing_the_report_charges_the_study_once_on_the_visits_bill(self):
        self.price("X-ray Chest PA")
        study_id = self.performed()

        first = self.sign(study_id)
        again = self.sign(study_id)

        self.assertEqual((first.status_code, again.status_code), (200, 400))
        line = self.lines(study_id).get()
        self.assertEqual((line.unit_price, line.category), (Decimal("350.50"), "imaging"))
        self.assertEqual((line.invoice.visit_id, line.invoice.total), (self.visit.pk, Decimal("350.50")))
        self.assertEqual(line.invoice.patient_id, self.patient.pk)

    def test_a_modality_price_applies_when_the_body_part_has_none(self):
        self.price("X-ray", "200.25")
        study_id = self.performed()
        self.sign(study_id)
        self.assertEqual(self.lines(study_id).get().unit_price, Decimal("200.25"))

    def test_ordered_performed_or_cancelled_studies_are_never_charged(self):
        self.price("X-ray Chest PA")
        self.order()
        self.performed()
        cancelled = self.order()
        self.assertEqual(self.step(self.doctor_user, cancelled, "cancel").status_code, 200)
        self.assertFalse(InvoiceItem.objects.filter(charge_key__startswith="imaging:").exists())

    def test_no_price_means_no_charge_an_audit_entry_and_a_row_in_unbilled_work(self):
        study_id = self.performed()
        self.assertEqual(self.sign(study_id).status_code, 200)

        self.assertFalse(self.lines(study_id).exists())
        self.assertTrue(AuditLog.objects.filter(action="billing.charge.unpriced", object_id=str(study_id),
                                                model_name="laboratory.ImagingStudy").exists())
        since = hospital_today() - timedelta(days=1)
        found = [r for r in find_unbilled(self.hospital.pk, since) if r["kind"] == "imaging"]
        self.assertEqual([(r["id"], r["priced"], r["service"]) for r in found], [(study_id, False, "X-ray Chest PA")])

        self.price("X-ray Chest PA")
        charged, _ = charge_unbilled(self.hospital.pk, since)
        charge_unbilled(self.hospital.pk, since)

        self.assertEqual([r["id"] for r in charged if r["kind"] == "imaging"], [study_id])
        self.assertEqual(self.lines(study_id).count(), 1)


class ImagingUploadTests(RadiologyFixture):
    def test_radiology_staff_attach_an_image_to_a_performed_study(self):
        study_id = self.performed()

        response = self.upload(self.radiographer, study_id)

        self.assertEqual(response.status_code, 201, response.content)
        document = PatientDocument.objects.get(pk=response.data["id"])
        self.assertEqual((document.imaging_study_id, document.patient_id, document.hospital_id, document.folder),
                         (study_id, self.patient.pk, self.hospital.pk, "imaging"))
        self.assertTrue(AuditLog.objects.filter(action="laboratory.imagingstudy.image_uploaded",
                                                object_id=str(study_id)).exists())
        listed = self.call(self.doctor_user, "get", f"{URL}{study_id}/images/")
        self.assertEqual([row["id"] for row in listed.data], [document.pk])
        self.assertNotIn("/media/", str(listed.data))

    def test_unsafe_or_wrong_files_are_refused(self):
        study_id = self.performed()
        cases = {
            "an executable": ("scan.exe", b"MZ\x90\x00" + b"\x00" * 64, "application/octet-stream"),
            "a script named .png": ("scan.png", b"#!/bin/sh\nrm -rf /\n", "image/png"),
            "a text file": ("notes.txt", b"plain text", "text/plain"),
            "an empty file": ("empty.png", b"", "image/png"),
        }
        for label, (name, content, kind) in cases.items():
            with self.subTest(label):
                self.assertEqual(self.upload(self.radiographer, study_id, name, content, kind).status_code, 400)
        self.assertFalse(PatientDocument.objects.filter(imaging_study_id=study_id).exists())

    def test_a_file_over_the_size_limit_is_refused(self):
        from laboratory import imaging_files

        study_id = self.performed()
        original = imaging_files.MAX_IMAGE_BYTES
        imaging_files.MAX_IMAGE_BYTES = len(PNG) - 1
        try:
            response = self.upload(self.radiographer, study_id)
        finally:
            imaging_files.MAX_IMAGE_BYTES = original
        self.assertEqual(response.status_code, 400)
        self.assertIn("MB", str(response.data))

    def test_who_may_upload(self):
        study_id = self.performed()
        pharmacist = staff("p5_ph", StaffRole.PHARMACIST, (self.hospital, StaffRole.PHARMACIST))
        nurse = staff("p5_nu", StaffRole.NURSE, (self.hospital, StaffRole.NURSE))
        self.assertEqual(self.upload(pharmacist, study_id).status_code, 403)
        self.assertEqual(self.upload(nurse, study_id).status_code, 403)
        self.assertEqual(self.upload(self.lab_tech, study_id).status_code, 201)

    def test_a_signed_or_cancelled_study_takes_no_more_images(self):
        signed = self.performed()
        self.sign(signed)
        cancelled = self.order()
        self.step(self.doctor_user, cancelled, "cancel")
        self.assertEqual(self.upload(self.radiographer, signed).status_code, 400)
        self.assertEqual(self.upload(self.radiographer, cancelled).status_code, 400)

    def test_images_are_served_privately_and_only_to_those_allowed(self):
        study_id = self.performed()
        doc_id = self.upload(self.radiographer, study_id).data["id"]
        url = f"{URL}{study_id}/images/{doc_id}/"
        pharmacist = staff("p5_ph2", StaffRole.PHARMACIST, (self.hospital, StaffRole.PHARMACIST))
        outsider = staff("p5_doc_b", StaffRole.DOCTOR, (self.other, StaffRole.DOCTOR))

        ok = self.call(self.doctor_user, "get", url)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual((ok["Cache-Control"], ok["X-Content-Type-Options"]), ("private, no-store", "nosniff"))
        self.assertEqual(b"".join(ok.streaming_content), PNG)
        self.assertEqual(self.call(pharmacist, "get", url).status_code, 403)
        self.assertEqual(self.call(outsider, "get", url, hospital=self.other).status_code, 404)
        self.assertTrue(AuditLog.objects.filter(action="laboratory.imagingstudy.image_read",
                                                object_id=str(study_id)).exists())

    def test_the_patient_sees_images_only_after_the_report_is_signed(self):
        from django.contrib.auth import get_user_model

        study_id = self.performed()
        doc_id = self.upload(self.radiographer, study_id).data["id"]
        login = get_user_model().objects.create_user(username="p5_patient", password="x")
        self.patient.user = login
        self.patient.save(update_fields=["user"])
        url = f"{URL}{study_id}/images/{doc_id}/"

        before = self.call(login, "get", url)
        listed_before = self.call(login, "get", "/api/documents/")
        self.sign(study_id)
        after = self.call(login, "get", url)

        listed_after = self.call(login, "get", "/api/documents/")

        self.assertEqual(before.status_code, 404)
        self.assertNotIn(doc_id, [row["id"] for row in listed_before.data["documents"]])
        self.assertEqual(after.status_code, 200)
        self.assertIn(doc_id, [row["id"] for row in listed_after.data["documents"]])
