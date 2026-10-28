"""Radiology / imaging workflow (G4)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from doctors.models import Doctor
from hospital.models import Hospital
from laboratory.models import ImagingStudy
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import put_in_care
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
URL = "/api/laboratory/imaging/"


def staff(username, role, *hospitals):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=username, is_active_staff=True)
    for hospital, hospital_role in hospitals:
        StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=hospital_role, is_active=True)
    return user


def rows(response):
    return response.data.get("results", response.data)


class ImagingTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="A", is_active=True)
        self.other = Hospital.objects.create(name="B", is_active=True)
        self.patient = Patient.objects.create(name="Asha", age=40, gender="Female", phone="9999999999", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="U1", is_active=True)
        self.doctor_user = staff("doc", StaffRole.DOCTOR, (self.hospital, StaffRole.DOCTOR))
        self.doctor = put_in_care(self.doctor_user, self.hospital, self.patient)
        self.radiologist = staff("rad", StaffRole.DOCTOR, (self.hospital, StaffRole.DOCTOR))
        Doctor.objects.create(user=self.radiologist, hospital=self.hospital, name="Dr Rad", specialization="Radiology", phone="9000000001")
        self.tech = staff("tech", StaffRole.LAB_STAFF, (self.hospital, StaffRole.LAB_STAFF))
        self.client = APIClient()

    def call(self, user, method, url, data=None, hospital=None):
        self.client.force_authenticate(user=user)
        header = {"HTTP_X_HOSPITAL_ID": str((hospital or self.hospital).pk)}
        return getattr(self.client, method)(url, data, format="json", **header)

    def order(self, **extra):
        data = {"patient": self.patient.pk, "modality": "X-ray", "body_part": "Chest PA", "indication": "Cough 3 weeks"}
        data.update(extra)
        return self.call(self.doctor_user, "post", URL, data)

    def step(self, user, study_id, action, data=None):
        return self.call(user, "post", f"{URL}{study_id}/{action}/", data or {})

    def test_full_workflow_order_schedule_perform_report(self):
        created = self.order()
        study_id = created.data["id"]

        scheduled = self.step(self.tech, study_id, "schedule", {"scheduled_for": "2026-10-29T10:00:00+05:30"})
        performed = self.step(self.tech, study_id, "perform", {"technician_notes": "Good inspiration"})
        reported = self.step(self.radiologist, study_id, "report", {"findings": "Clear lungs.", "impression": "Normal chest."})

        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertTrue(created.data["accession_number"].startswith("RAD"))
        self.assertEqual(created.data["ordered_by"], self.doctor.pk)
        self.assertEqual(
            (scheduled.data["status"], performed.data["status"], reported.data["status"]),
            ("Scheduled", "Performed", "Reported"),
        )
        self.assertEqual(reported.data["reported_by_name"], "Dr Rad")

    def test_only_doctors_order_and_only_technicians_perform(self):
        refused_order = self.call(
            self.tech, "post", URL, {"patient": self.patient.pk, "modality": "CT", "body_part": "Head", "indication": "Fall"}
        )
        study_id = self.order().data["id"]
        refused_perform = self.step(self.doctor_user, study_id, "perform")

        self.assertEqual(refused_order.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(refused_perform.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_needs_performed_study_and_both_parts(self):
        study_id = self.order().data["id"]

        # The ordering doctor can see the study; a radiologist only once performed.
        too_early = self.step(self.doctor_user, study_id, "report", {"findings": "x", "impression": "y"})
        hidden = self.step(self.radiologist, study_id, "report", {"findings": "x", "impression": "y"})
        self.step(self.tech, study_id, "perform")
        half = self.step(self.radiologist, study_id, "report", {"findings": "Clear."})

        self.assertEqual(too_early.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(half.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signed_report_cannot_change_or_be_cancelled(self):
        study_id = self.order().data["id"]
        self.step(self.tech, study_id, "perform")
        self.step(self.radiologist, study_id, "report", {"findings": "Clear.", "impression": "Normal."})

        again = self.step(self.radiologist, study_id, "report", {"findings": "Changed", "impression": "Changed"})
        cancelled = self.step(self.doctor_user, study_id, "cancel")
        patched = self.call(self.radiologist, "patch", f"{URL}{study_id}/", {"impression": "x"})

        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(cancelled.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(patched.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(ImagingStudy.objects.get().impression, "Normal.")

    def test_radiologist_sees_performed_studies_outside_their_care_only(self):
        ordered_id = self.order().data["id"]
        performed_id = self.order(body_part="Abdomen").data["id"]
        self.step(self.tech, performed_id, "perform")

        listed = self.call(self.radiologist, "get", URL)

        ids = [row["id"] for row in rows(listed)]
        self.assertEqual(ids, [performed_id])
        self.assertNotIn(ordered_id, ids)

    def test_worklist_never_widens_to_another_hospitals_role(self):
        # Doctor in B, Lab Staff in A: must not report A's study.
        mixed = staff("mixed", StaffRole.DOCTOR, (self.other, StaffRole.DOCTOR), (self.hospital, StaffRole.LAB_STAFF))
        Doctor.objects.create(user=mixed, hospital=self.other, name="Dr Mixed", specialization="Radiology", phone="9000000002")
        study_id = self.order().data["id"]
        self.step(self.tech, study_id, "perform")

        refused = self.step(mixed, study_id, "report", {"findings": "x", "impression": "y"})

        self.assertIn(refused.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.assertEqual(ImagingStudy.objects.get().status, "Performed")

    def test_patient_sees_only_signed_reports(self):
        shown = self.order().data["id"]
        self.order(body_part="Knee")
        self.step(self.tech, shown, "perform")
        self.step(self.radiologist, shown, "report", {"findings": "Clear.", "impression": "Normal."})
        login = User.objects.create_user(username="asha", password="testpass123")
        self.patient.user = login
        self.patient.save(update_fields=["user"])
        self.client.force_authenticate(user=login)

        listed = self.client.get(URL)

        self.assertEqual([row["id"] for row in rows(listed)], [shown])

    def test_other_hospital_cannot_see_studies(self):
        self.order()
        outsider = staff("doc_b", StaffRole.DOCTOR, (self.other, StaffRole.DOCTOR))

        listed = self.call(outsider, "get", URL, hospital=self.other)

        self.assertEqual(rows(listed), [])
