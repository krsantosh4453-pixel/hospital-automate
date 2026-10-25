"""Role, write-path and audit checks across two synthetic hospitals."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import VitalSign
from encounters.models import Visit
from hospital.models import Department, Hospital, Ward
from patients.models import Patient, PatientDocument, PatientHospital
from users.models import StaffHospitalMembership, StaffRole

from .test_tenant_isolation import make_staff


class TwoHospitalCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital_a = Hospital.objects.create(name="Synthetic A", is_active=True)
        cls.hospital_b = Hospital.objects.create(name="Synthetic B", is_active=True)
        cls.patient = Patient.objects.create(
            name="Synthetic Patient", age=30, gender="Male", phone="9000000002",
            hospital=cls.hospital_a,
        )
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital_a, uhid="A-9")
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital_b, uhid="B-9")
        cls.visit_a = Visit.objects.create(patient=cls.patient, hospital=cls.hospital_a)
        cls.visit_b = Visit.objects.create(patient=cls.patient, hospital=cls.hospital_b)

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        if hospital is not None:
            client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client


class RolePerHospitalTests(TwoHospitalCase):
    """A role held in one hospital grants nothing in another."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user, profile = make_staff("mixed", cls.hospital_a, role=StaffRole.DOCTOR)
        StaffHospitalMembership.objects.create(
            staff=profile, hospital=cls.hospital_b, role=StaffRole.RECEPTIONIST, is_active=True
        )

    def test_doctor_in_a_can_record_vitals_in_a(self):
        resp = self.client_for(self.user, self.hospital_a).post(
            "/api/clinical/vitals/", {"visit": self.visit_a.id, "heart_rate": 72}, format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_receptionist_in_b_cannot_record_vitals_in_b(self):
        resp = self.client_for(self.user, self.hospital_b).post(
            "/api/clinical/vitals/", {"visit": self.visit_b.id, "heart_rate": 72}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(VitalSign.objects.filter(visit=self.visit_b).exists())

    def _vital_ids(self, resp):
        body = resp.json()
        rows = body.get("results", body) if isinstance(body, dict) else body
        return {row["id"] for row in rows}

    def test_list_without_hospital_only_covers_hospitals_where_role_allows_it(self):
        vital_a = VitalSign.objects.create(visit=self.visit_a, heart_rate=70)
        vital_b = VitalSign.objects.create(visit=self.visit_b, heart_rate=80)
        resp = self.client_for(self.user).get("/api/clinical/vitals/")
        self.assertEqual(resp.status_code, 200, resp.content)
        ids = self._vital_ids(resp)
        self.assertIn(vital_a.id, ids)
        self.assertNotIn(vital_b.id, ids)

    def test_detail_without_hospital_refuses_row_where_role_does_not_allow_it(self):
        vital_b = VitalSign.objects.create(visit=self.visit_b, heart_rate=80)
        resp = self.client_for(self.user).get(f"/api/clinical/vitals/{vital_b.id}/")
        self.assertIn(resp.status_code, (403, 404))

    def test_doctor_role_does_not_follow_object_into_b(self):
        vital = VitalSign.objects.create(visit=self.visit_b, heart_rate=80)
        resp = self.client_for(self.user).patch(
            f"/api/clinical/vitals/{vital.id}/", {"heart_rate": 90}, format="json"
        )
        self.assertIn(resp.status_code, (403, 404))
        vital.refresh_from_db()
        self.assertEqual(vital.heart_rate, 80)

    def test_hospital_header_for_foreign_hospital_is_rejected(self):
        outsider = Hospital.objects.create(name="Synthetic C", is_active=True)
        resp = self.client_for(self.user, outsider).get("/api/encounters/visits/")
        self.assertEqual(resp.status_code, 403)


class RelatedObjectWriteTests(TwoHospitalCase):
    """Ids of another hospital's rows cannot be smuggled into a write."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.doctor_a, _ = make_staff("doctor_a", cls.hospital_a, role=StaffRole.DOCTOR)

    def test_vitals_against_foreign_visit_rejected(self):
        resp = self.client_for(self.doctor_a).post(
            "/api/clinical/vitals/", {"visit": self.visit_b.id, "heart_rate": 70}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(VitalSign.objects.filter(visit=self.visit_b).exists())

    def test_visit_for_patient_not_registered_here_rejected(self):
        stranger = Patient.objects.create(
            name="Synthetic Stranger", age=50, gender="Female", phone="9000000003",
            hospital=self.hospital_b,
        )
        PatientHospital.objects.create(patient=stranger, hospital=self.hospital_b, uhid="B-77")
        resp = self.client_for(self.doctor_a).post(
            "/api/encounters/visits/",
            {"patient": stranger.id, "hospital": self.hospital_a.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)


class OrganisationStructureTests(TwoHospitalCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.reception_a, _ = make_staff("reception_a", cls.hospital_a, role=StaffRole.RECEPTIONIST)
        cls.admin_a, _ = make_staff("org_admin_a", cls.hospital_a, role=StaffRole.ADMIN)

    def test_staff_cannot_create_hospital(self):
        resp = self.client_for(self.admin_a).post("/api/hospital/hospitals/", {"name": "Rogue"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Hospital.objects.filter(name="Rogue").exists())

    def test_staff_only_list_own_hospitals(self):
        resp = self.client_for(self.reception_a).get("/api/hospital/hospitals/")
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertEqual(ids, {self.hospital_a.id})

    def test_staff_cannot_edit_other_hospital(self):
        resp = self.client_for(self.admin_a).patch(
            f"/api/hospital/hospitals/{self.hospital_b.id}/", {"name": "Renamed"}, format="json"
        )
        self.assertEqual(resp.status_code, 404)

    def test_receptionist_cannot_create_ward(self):
        resp = self.client_for(self.reception_a).post(
            "/api/hospital/wards/", {"hospital": self.hospital_a.id, "name": "W1"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_creates_ward_only_in_own_hospital(self):
        client = self.client_for(self.admin_a)
        own = client.post("/api/hospital/wards/", {"hospital": self.hospital_a.id, "name": "W1"}, format="json")
        self.assertEqual(own.status_code, 201, own.content)
        foreign = client.post("/api/hospital/wards/", {"hospital": self.hospital_b.id, "name": "W2"}, format="json")
        self.assertEqual(foreign.status_code, 403)
        self.assertFalse(Ward.objects.filter(name="W2").exists())

    def test_department_head_must_be_local_doctor(self):
        from doctors.models import Doctor
        foreign = Doctor.objects.create(hospital=self.hospital_b, name="Dr Elsewhere", specialization="GP", phone="9000000090")
        local = Doctor.objects.create(hospital=self.hospital_a, name="Dr Here", specialization="GP", phone="9000000091")
        client = self.client_for(self.admin_a)
        bad = client.post("/api/hospital/departments/", {"hospital": self.hospital_a.id, "name": "Cardio", "head": foreign.id}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = client.post("/api/hospital/departments/", {"hospital": self.hospital_a.id, "name": "Cardio", "code": "CARD", "head": local.id}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.json()["head_name"], "Dr Here")

    def test_department_of_other_hospital_not_editable(self):
        dept = Department.objects.create(hospital=self.hospital_b, name="Synthetic Dept")
        resp = self.client_for(self.admin_a).delete(f"/api/hospital/departments/{dept.id}/")
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Department.objects.filter(pk=dept.pk).exists())


class AuditTrailTests(TwoHospitalCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.doctor_a, _ = make_staff("audit_doctor", cls.hospital_a, role=StaffRole.DOCTOR)

    def test_clinical_write_creates_hospital_scoped_audit_row(self):
        resp = self.client_for(self.doctor_a).post(
            "/api/clinical/vitals/", {"visit": self.visit_a.id, "spo2": 98}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        log = AuditLog.objects.get(action="clinical.vitalsign.create")
        self.assertEqual(log.user, self.doctor_a)
        self.assertEqual(log.hospital_id, self.hospital_a.id)
        self.assertEqual(log.object_id, str(resp.json()["id"]))


@override_settings(MEDIA_ROOT="/tmp/hms-test-media")
class SharedPatientDocumentTests(TwoHospitalCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.doctor_a, _ = make_staff("doc_owner_a", cls.hospital_a, role=StaffRole.DOCTOR)
        cls.doctor_b, _ = make_staff("doc_owner_b", cls.hospital_b, role=StaffRole.DOCTOR)

    def test_document_uploaded_in_b_not_visible_in_a(self):
        upload = SimpleUploadedFile("note.txt", b"synthetic", content_type="text/plain")
        resp = self.client_for(self.doctor_b, self.hospital_b).post(
            f"/api/patients/{self.patient.id}/documents/", {"file": upload, "title": "B only"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(PatientDocument.objects.get().hospital_id, self.hospital_b.id)

        listed = self.client_for(self.doctor_a, self.hospital_a).get(
            f"/api/patients/{self.patient.id}/documents/"
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [])


class PatientDeleteTests(TwoHospitalCase):
    """
    A patient is shared across hospitals and clinical rows cascade from
    Patient, so one hospital must never delete another hospital's records.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.receptionist_a, _ = make_staff("del_recep", cls.hospital_a, role=StaffRole.RECEPTIONIST)
        cls.admin_a, _ = make_staff("del_admin", cls.hospital_a, role=StaffRole.ADMIN)

    def test_receptionist_cannot_delete_patient_shared_with_another_hospital(self):
        resp = self.client_for(self.receptionist_a, self.hospital_a).delete(f"/api/patients/{self.patient.id}/")
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertTrue(Patient.objects.filter(pk=self.patient.pk).exists())
        self.assertTrue(Visit.objects.filter(pk=self.visit_b.pk).exists())

    def test_admin_cannot_delete_patient_registered_at_another_hospital(self):
        resp = self.client_for(self.admin_a, self.hospital_a).delete(f"/api/patients/{self.patient.id}/")
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertTrue(Patient.objects.filter(pk=self.patient.pk).exists())
        self.assertTrue(Visit.objects.filter(pk=self.visit_b.pk).exists())

    def test_admin_cannot_delete_patient_with_records_at_another_hospital(self):
        PatientHospital.objects.filter(patient=self.patient, hospital=self.hospital_b).delete()
        resp = self.client_for(self.admin_a, self.hospital_a).delete(f"/api/patients/{self.patient.id}/")
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertTrue(Visit.objects.filter(pk=self.visit_b.pk).exists())

    def test_admin_can_delete_patient_known_only_to_own_hospital(self):
        local = Patient.objects.create(
            name="Synthetic Local", age=40, gender="Female", phone="9000000077", hospital=self.hospital_a,
        )
        PatientHospital.objects.create(patient=local, hospital=self.hospital_a, uhid="A-77")
        resp = self.client_for(self.admin_a, self.hospital_a).delete(f"/api/patients/{local.id}/")
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertFalse(Patient.objects.filter(pk=local.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="patients.patient.delete").exists())
