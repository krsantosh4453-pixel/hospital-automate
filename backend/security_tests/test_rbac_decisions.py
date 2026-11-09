"""
Owner's RBAC decisions of 2026-11-09 (docs/architecture/phase-3-rbac-decisions-plan.md),
with the recommended answers to Q1-Q6. Synthetic data only.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from doctors.models import Doctor
from hospital.models import Hospital
from users.models import StaffRole
from users.permissions import get_user_roles

from .test_tenant_isolation import make_staff

User = get_user_model()


def client_for(user, hospital):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
    return client


class ManagerRoleAssignmentTests(TestCase):
    """Decision 1 and Q1: what a Hospital Manager may hand out, always audited."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic RBAC", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic RBAC Other", is_active=True)
        cls.admin, _ = make_staff("rbac_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.manager, _ = make_staff("rbac_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.peer, _ = make_staff("rbac_peer_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.staff, _ = make_staff("rbac_staff", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.outsider, _ = make_staff("rbac_outsider", cls.other, role=StaffRole.RECEPTIONIST)

    def assign(self, actor, target, role, hospital=None):
        return client_for(actor, hospital or self.hospital).patch(
            f"/api/v1/users/{target.id}/membership/", {"role": role}, format="json")

    def test_a_manager_assigns_clinical_and_operational_roles(self):
        for role in (StaffRole.DOCTOR, StaffRole.NURSE, StaffRole.PHARMACIST, StaffRole.COMPOUNDER,
                     StaffRole.LAB_STAFF, StaffRole.BILLING_STAFF, StaffRole.INVENTORY_STAFF,
                     StaffRole.BLOOD_BANK_STAFF, StaffRole.RECEPTIONIST):
            self.assertEqual(self.assign(self.manager, self.staff, role).status_code, 200, role)

    def test_a_manager_cannot_create_admins_or_managers(self):
        for role in (StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER):
            self.assertEqual(self.assign(self.manager, self.staff, role).status_code, 403, role)
        self.assertEqual(get_user_roles(self.staff, self.hospital.id), [StaffRole.RECEPTIONIST])

    def test_a_manager_cannot_change_another_manager(self):
        self.assertEqual(self.assign(self.manager, self.peer, StaffRole.RECEPTIONIST).status_code, 403)
        self.assertEqual(get_user_roles(self.peer, self.hospital.id), [StaffRole.HOSPITAL_MANAGER])

    def test_an_admin_assigns_hospital_manager(self):
        self.assertEqual(self.assign(self.admin, self.staff, StaffRole.HOSPITAL_MANAGER).status_code, 200)

    def test_a_manager_cannot_assign_at_another_hospital(self):
        response = self.assign(self.manager, self.outsider, StaffRole.DOCTOR, hospital=self.other)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(get_user_roles(self.outsider, self.other.id), [StaffRole.RECEPTIONIST])

    def test_a_manager_cannot_invite_an_admin_or_manager(self):
        for role in (StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER):
            response = client_for(self.manager, self.hospital).post(
                "/api/v1/users/invite/", {"name": "X", "email": f"{role[:3].lower()}@example.test", "role": role},
                format="json")
            self.assertEqual(response.status_code, 403, role)

    def test_invitations_and_role_changes_are_audited(self):
        invited = client_for(self.manager, self.hospital).post(
            "/api/v1/users/invite/", {"name": "Synthetic Nurse", "email": "nurse@example.test", "role": "Nurse",
                                     "phone": "9000000082"},
            format="json")
        self.assertEqual(invited.status_code, 201, invited.content)
        self.assign(self.manager, self.staff, StaffRole.BILLING_STAFF)

        actions = set(AuditLog.objects.filter(hospital=self.hospital).values_list("action", flat=True))
        self.assertTrue({"users.staff.invited", "users.staff.membership_changed"} <= actions, actions)


class DoctorVerificationTests(TestCase):
    """Decision 1 and Q2: the hospital Admin records a doctor's registration check."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Verify", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Verify Other", is_active=True)
        cls.admin, _ = make_staff("verify_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.manager, _ = make_staff("verify_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.other_admin, _ = make_staff("verify_other_admin", cls.other, role=StaffRole.ADMIN)
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, name="Dr Verify", specialization="General",
                                           phone="9000000080", registration_number="KMC-12345")

    def verify(self, actor, hospital=None, doctor=None, body=None):
        doctor = doctor or self.doctor
        return client_for(actor, hospital or self.hospital).post(
            f"/api/v1/doctors/{doctor.id}/verify-registration/", body or {"registration_council": "KMC"}, format="json")

    def test_the_admin_verifies_and_it_is_audited(self):
        response = self.verify(self.admin)

        self.assertEqual(response.status_code, 200, response.content)
        self.doctor.refresh_from_db()
        self.assertEqual((self.doctor.registration_verified_by, self.doctor.registration_council), (self.admin, "KMC"))
        self.assertIsNotNone(self.doctor.registration_verified_at)
        self.assertTrue(AuditLog.objects.filter(action="doctors.registration_verified", hospital=self.hospital).exists())

    def test_a_manager_or_another_hospitals_admin_cannot_verify(self):
        self.assertEqual(self.verify(self.manager).status_code, 403)
        self.assertIn(self.verify(self.other_admin, hospital=self.other).status_code, (403, 404))
        self.assertIn(self.verify(self.other_admin, hospital=self.hospital).status_code, (403, 404))
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.registration_verified_at)

    def test_a_doctor_without_a_registration_number_cannot_be_verified(self):
        unregistered = Doctor.objects.create(hospital=self.hospital, name="Dr None", specialization="General",
                                             phone="9000000081")
        self.assertEqual(self.verify(self.admin, doctor=unregistered).status_code, 400)

    def test_changing_the_registration_number_clears_the_verification(self):
        self.verify(self.admin)

        response = client_for(self.admin, self.hospital).patch(f"/api/v1/doctors/{self.doctor.id}/",
                                                               {"registration_number": "KMC-99999"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.registration_verified_at)

    def test_verification_fields_cannot_be_set_through_the_doctor_form(self):
        client_for(self.admin, self.hospital).patch(f"/api/v1/doctors/{self.doctor.id}/",
                                                    {"registration_verified_at": "2026-01-01T00:00:00Z"}, format="json")
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.registration_verified_at)

    def test_only_the_admin_switches_the_verified_doctors_rule(self):
        url = f"/api/v1/hospital/hospitals/{self.hospital.id}/"
        self.assertEqual(client_for(self.manager, self.hospital).patch(
            url, {"require_verified_doctors": True}, format="json").status_code, 403)
        self.assertEqual(client_for(self.admin, self.hospital).patch(
            url, {"require_verified_doctors": True}, format="json").status_code, 200)
        self.hospital.refresh_from_db()
        self.assertTrue(self.hospital.require_verified_doctors)


class ClinicalWriteRulesTests(TestCase):
    """Decision 2 with Q4-Q6: who writes which clinical record; signed records stay as signed."""

    @classmethod
    def setUpTestData(cls):
        from encounters.models import Visit
        from patients.models import Patient, PatientHospital

        cls.hospital = Hospital.objects.create(name="Synthetic Clinical", is_active=True)
        cls.admin, _ = make_staff("clin_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.manager, _ = make_staff("clin_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.nurse, _ = make_staff("clin_nurse", cls.hospital, role=StaffRole.NURSE)
        cls.pharmacist, _ = make_staff("clin_pharmacist", cls.hospital, role=StaffRole.PHARMACIST)
        cls.doctor_user, _ = make_staff("clin_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.other_doctor_user, _ = make_staff("clin_doctor_two", cls.hospital, role=StaffRole.DOCTOR)
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, user=cls.doctor_user, name="Dr Author",
                                           specialization="Medicine", phone="9000000090", registration_number="R-1")
        cls.other_doctor = Doctor.objects.create(hospital=cls.hospital, user=cls.other_doctor_user, name="Dr Other",
                                                 specialization="Medicine", phone="9000000091")
        cls.patient = Patient.objects.create(name="Synthetic Clinical Patient", age=50, gender="Female",
                                             phone="9000000092", hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="CLIN-1")
        cls.visit = Visit.objects.create(hospital=cls.hospital, patient=cls.patient, doctor=cls.doctor)
        Visit.objects.create(hospital=cls.hospital, patient=cls.patient, doctor=cls.other_doctor)

    def api(self, user):
        return client_for(user, self.hospital)

    def note(self, user=None, **extra):
        return self.api(user or self.doctor_user).post("/api/v1/clinical/clinical-notes/", {
            "visit": self.visit.id, "assessment": "Synthetic assessment", **extra}, format="json")

    def prescribe(self, user=None):
        return self.api(user or self.doctor_user).post("/api/v1/clinical/prescriptions/", {
            "hospital": self.hospital.id, "patient": self.patient.id, "visit": self.visit.id,
            "items": [{"name": "Synthetic Paracetamol 500", "dosage": "1 tab", "frequency": "TDS",
                       "duration": "3 days", "quantity": 9}]}, format="json")

    # Admin and Manager: read, never write --------------------------------

    def test_admin_and_manager_cannot_write_clinical_records(self):
        for path in ("vitals", "allergies", "clinical-notes", "diagnoses", "procedures", "medical-records",
                     "prescriptions", "prescription-items", "immunizations", "service-orders"):
            for user in (self.admin, self.manager):
                response = self.api(user).post(f"/api/v1/clinical/{path}/", {"visit": self.visit.id}, format="json")
                self.assertEqual(response.status_code, 403, f"{user.username} POST {path}")

    def test_admin_reads_clinical_records(self):
        self.assertEqual(self.note().status_code, 201)
        for path in ("clinical-notes", "diagnoses", "medical-records", "prescriptions"):
            self.assertEqual(self.api(self.admin).get(f"/api/v1/clinical/{path}/").status_code, 200, path)

    def test_admin_cannot_change_a_doctors_note_or_prescription(self):
        note = self.note().json()["id"]
        rx = self.prescribe().json()["id"]

        self.assertEqual(self.api(self.admin).patch(f"/api/v1/clinical/clinical-notes/{note}/", {"plan": "x"},
                                                    format="json").status_code, 403)
        self.assertEqual(self.api(self.admin).patch(f"/api/v1/clinical/prescriptions/{rx}/", {"notes": "x"},
                                                    format="json").status_code, 403)

    # Authorship ----------------------------------------------------------

    def test_a_note_is_always_written_in_the_signed_in_doctors_name(self):
        response = self.note(doctor=self.other_doctor.id)

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["doctor"], self.doctor.id)

    def test_another_doctor_cannot_edit_or_sign_my_note(self):
        note = self.note().json()["id"]
        other = self.api(self.other_doctor_user)

        self.assertEqual(other.patch(f"/api/v1/clinical/clinical-notes/{note}/", {"plan": "x"},
                                     format="json").status_code, 403)
        self.assertEqual(other.post(f"/api/v1/clinical/clinical-notes/{note}/sign/").status_code, 403)

    def test_another_doctor_cannot_change_my_prescription(self):
        rx = self.prescribe().json()["id"]

        response = self.api(self.other_doctor_user).patch(f"/api/v1/clinical/prescriptions/{rx}/",
                                                          {"notes": "x"}, format="json")

        self.assertEqual(response.status_code, 403)

    # Signing --------------------------------------------------------------

    def test_a_signed_note_is_locked_and_a_correction_keeps_both(self):
        from clinical.models import ClinicalNote

        doctor = self.api(self.doctor_user)
        note = self.note().json()["id"]
        self.assertEqual(doctor.patch(f"/api/v1/clinical/clinical-notes/{note}/", {"plan": "Draft edit"},
                                      format="json").status_code, 200)

        signed = doctor.post(f"/api/v1/clinical/clinical-notes/{note}/sign/")
        self.assertEqual(signed.status_code, 200, signed.content)
        self.assertEqual(doctor.patch(f"/api/v1/clinical/clinical-notes/{note}/", {"plan": "Late edit"},
                                      format="json").status_code, 409)
        self.assertEqual(doctor.post(f"/api/v1/clinical/clinical-notes/{note}/sign/").status_code, 409)

        amendment = self.note(amends=note, plan="Corrected plan")
        self.assertEqual(amendment.status_code, 201, amendment.content)
        original = ClinicalNote.objects.get(pk=note)
        self.assertEqual((original.plan, original.signed_by), ("Draft edit", self.doctor_user))
        self.assertEqual(ClinicalNote.objects.get(pk=amendment.json()["id"]).amends_id, note)
        self.assertTrue(AuditLog.objects.filter(action="clinical.clinicalnote.signed").exists())

    def test_a_signed_diagnosis_is_locked(self):
        doctor = self.api(self.doctor_user)
        diagnosis = doctor.post("/api/v1/clinical/diagnoses/", {"visit": self.visit.id, "name": "Viral fever"},
                                format="json").json()["id"]

        self.assertEqual(doctor.post(f"/api/v1/clinical/diagnoses/{diagnosis}/sign/").status_code, 200)

        self.assertEqual(doctor.patch(f"/api/v1/clinical/diagnoses/{diagnosis}/", {"name": "x"},
                                      format="json").status_code, 409)

    def test_an_unverified_doctor_cannot_sign_or_prescribe_where_verification_is_required(self):
        Hospital.objects.filter(pk=self.hospital.pk).update(require_verified_doctors=True)
        note = self.note().json()["id"]

        self.assertEqual(self.api(self.doctor_user).post(f"/api/v1/clinical/clinical-notes/{note}/sign/")
                         .status_code, 403)
        self.assertEqual(self.prescribe().status_code, 403)

        self.api(self.admin).post(f"/api/v1/doctors/{self.doctor.id}/verify-registration/", {}, format="json")
        self.assertEqual(self.api(self.doctor_user).post(f"/api/v1/clinical/clinical-notes/{note}/sign/")
                         .status_code, 200)
        self.assertEqual(self.prescribe().status_code, 201)

    # Prescriptions --------------------------------------------------------

    def test_changing_a_prescription_keeps_every_earlier_version(self):
        doctor = self.api(self.doctor_user)
        rx = self.prescribe().json()["id"]

        changed = doctor.patch(f"/api/v1/clinical/prescriptions/{rx}/", {"items": [
            {"name": "Synthetic Paracetamol 650", "dosage": "1 tab", "frequency": "BD", "duration": "3 days",
             "quantity": 6}]}, format="json")

        self.assertEqual(changed.status_code, 200, changed.content)
        revisions = doctor.get(f"/api/v1/clinical/prescriptions/{rx}/revisions/").json()["revisions"]
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0]["changed_by"], self.doctor_user.id)
        self.assertEqual([item["name"] for item in revisions[0]["content"]["items"]], ["Synthetic Paracetamol 500"])

    def test_a_pharmacist_reads_but_cannot_change_a_prescription(self):
        rx = self.prescribe().json()["id"]
        pharmacist = self.api(self.pharmacist)

        self.assertEqual(pharmacist.get(f"/api/v1/clinical/prescriptions/{rx}/").status_code, 200)
        self.assertEqual(pharmacist.patch(f"/api/v1/clinical/prescriptions/{rx}/", {"notes": "x"},
                                          format="json").status_code, 403)

    def test_only_a_pharmacist_transcribes_paper_prescriptions(self):
        response = self.api(self.admin).post("/api/v1/clinical/prescriptions/transcribe/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(self.api(self.pharmacist).post("/api/v1/clinical/prescriptions/transcribe/", {},
                                                           format="json").status_code, 403)

    # Nurses ----------------------------------------------------------------

    def test_a_nurse_writes_nursing_entries_but_not_doctors_notes(self):
        nurse = self.api(self.nurse)
        self.assertEqual(self.note(user=self.nurse).status_code, 403)
        self.assertNotEqual(nurse.post("/api/v1/nurses/notes/", {}, format="json").status_code, 403)
        self.assertNotEqual(nurse.post("/api/v1/clinical/medical-records/", {}, format="json").status_code, 403)
