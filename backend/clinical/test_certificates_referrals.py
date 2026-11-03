"""Medical certificates (D10) and referrals (D11)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from clinical.models import MedicalCertificate, Referral
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import put_in_care
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()

CERTIFICATES = "/api/clinical/certificates/"
REFERRALS = "/api/clinical/referrals/"


def make_staff(username, hospital, role, with_doctor_profile=False):
    user = User.objects.create_user(username=username, password="testpass123")
    profile = StaffProfile.objects.create(user=user, role=role, employee_id=username, is_active_staff=True)
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    doctor = None
    if with_doctor_profile:
        doctor = Doctor.objects.create(
            user=user, hospital=hospital, name=f"Dr. {username}", specialization="General", phone="9876543210"
        )
    return user, doctor


def make_patient(name, phone, hospital, uhid):
    patient = Patient.objects.create(name=name, age=34, gender="Female", phone=phone, hospital=hospital)
    PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=uhid, is_active=True)
    return patient


def rows(response):
    return response.data.get("results", response.data) if isinstance(response.data, dict) else response.data


class DocumentTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="Hospital A", address="1 Main Road", is_active=True)
        self.other_hospital = Hospital.objects.create(name="Hospital B", is_active=True)
        self.patient = make_patient("Asha", "9999999999", self.hospital, "U1")
        self.doctor_user, _ = make_staff("doc_a", self.hospital, StaffRole.DOCTOR)
        self.doctor = put_in_care(self.doctor_user, self.hospital, self.patient)
        self.colleague_user, self.colleague = make_staff("doc_c", self.hospital, StaffRole.DOCTOR, True)

    def as_user(self, user=None):
        self.client.force_authenticate(user=user or self.doctor_user)
        return {"HTTP_X_HOSPITAL_ID": str(self.hospital.pk)}

    def post(self, url, data, user=None):
        return self.client.post(url, data, format="json", **self.as_user(user))


class MedicalCertificateTests(DocumentTestBase):
    def certificate(self, **overrides):
        data = {
            "patient": self.patient.pk,
            "kind": "Sick leave",
            "diagnosis": "Viral fever",
            "start_date": "2026-10-20",
            "end_date": "2026-10-22",
        }
        data.update(overrides)
        return data

    def test_doctor_issues_certificate_signed_by_themselves(self):
        response = self.post(CERTIFICATES, self.certificate(doctor=self.colleague.pk))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        cert = MedicalCertificate.objects.get()
        self.assertEqual(cert.doctor, self.doctor)  # the request cannot pick the signer
        self.assertEqual(cert.hospital, self.hospital)
        self.assertEqual(response.data["hospital_address"], "1 Main Road")

    def test_sick_leave_needs_an_end_date(self):
        response = self.post(CERTIFICATES, self.certificate(end_date=None))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response.data["details"])

    def test_end_date_cannot_precede_start(self):
        response = self.post(CERTIFICATES, self.certificate(end_date="2026-10-19"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response.data["details"])

    def test_fitness_certificate_without_end_date(self):
        response = self.post(CERTIFICATES, self.certificate(kind="Fitness", end_date=None))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_admin_without_doctor_profile_cannot_sign(self):
        admin, _ = make_staff("admin_a", self.hospital, StaffRole.ADMIN)

        response = self.post(CERTIFICATES, self.certificate(), user=admin)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(MedicalCertificate.objects.count(), 0)

    def test_nurse_and_receptionist_cannot_issue(self):
        for role in (StaffRole.NURSE, StaffRole.RECEPTIONIST):
            user, _ = make_staff(f"{role}_a".lower(), self.hospital, role)

            response = self.post(CERTIFICATES, self.certificate(), user=user)

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, role)

    def test_patient_of_another_hospital_is_refused(self):
        stranger = make_patient("Bina", "8888888888", self.other_hospital, "B1")

        response = self.post(CERTIFICATES, self.certificate(patient=stranger.pk))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(MedicalCertificate.objects.count(), 0)

    def test_certificate_cannot_be_edited_or_deleted(self):
        self.post(CERTIFICATES, self.certificate())
        url = f"{CERTIFICATES}{MedicalCertificate.objects.get().pk}/"
        header = self.as_user()

        patched = self.client.patch(url, {"diagnosis": "changed"}, format="json", **header)
        deleted = self.client.delete(url, **header)

        self.assertEqual(patched.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(deleted.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_other_hospital_doctor_cannot_read(self):
        self.post(CERTIFICATES, self.certificate())
        outsider, _ = make_staff("doc_b", self.other_hospital, StaffRole.DOCTOR, True)
        self.client.force_authenticate(user=outsider)

        response = self.client.get(CERTIFICATES)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(rows(response), [])

    def test_patient_reads_only_their_own_certificates(self):
        self.post(CERTIFICATES, self.certificate())
        other = make_patient("Ravi", "7777777777", self.hospital, "U2")
        MedicalCertificate.objects.create(
            hospital=self.hospital, patient=other, doctor=self.doctor, kind="Fitness", start_date="2026-10-01"
        )
        login = User.objects.create_user(username="asha", password="testpass123")
        self.patient.user = login
        self.patient.save(update_fields=["user"])
        self.client.force_authenticate(user=login)

        listed = self.client.get(CERTIFICATES)
        created = self.client.post(CERTIFICATES, self.certificate(), format="json")

        self.assertEqual([row["patient"] for row in rows(listed)], [self.patient.pk])
        self.assertEqual(created.status_code, status.HTTP_403_FORBIDDEN)


class ReferralTests(DocumentTestBase):
    def referral(self, **overrides):
        data = {"patient": self.patient.pk, "reason": "Persistent chest pain", "urgency": "Urgent"}
        data.update(overrides)
        return data

    def test_refer_to_colleague(self):
        response = self.post(REFERRALS, self.referral(referred_to_doctor=self.colleague.pk))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        referral = Referral.objects.get()
        self.assertEqual(referral.referring_doctor, self.doctor)
        self.assertEqual(referral.status, Referral.Status.PENDING)
        self.assertEqual(response.data["referred_to_doctor_name"], self.colleague.name)

    def test_refer_outside(self):
        response = self.post(REFERRALS, self.referral(referred_to_external="City Cardiac Centre", specialty="Cardiology"))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_needs_exactly_one_target(self):
        neither = self.post(REFERRALS, self.referral())
        both = self.post(
            REFERRALS, self.referral(referred_to_doctor=self.colleague.pk, referred_to_external="City Cardiac Centre")
        )

        self.assertEqual(neither.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(both.status_code, status.HTTP_400_BAD_REQUEST)

    def test_needs_a_reason(self):
        response = self.post(REFERRALS, self.referral(reason=" ", referred_to_external="City Cardiac Centre"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_refer_to_another_hospitals_doctor(self):
        _, foreign_doctor = make_staff("doc_b", self.other_hospital, StaffRole.DOCTOR, True)

        response = self.post(REFERRALS, self.referral(referred_to_doctor=foreign_doctor.pk))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Referral.objects.count(), 0)

    def test_only_status_changes_after_creation(self):
        self.post(REFERRALS, self.referral(referred_to_doctor=self.colleague.pk))
        url = f"{REFERRALS}{Referral.objects.get().pk}/"
        header = self.as_user()

        accepted = self.client.patch(url, {"status": "Accepted"}, format="json", **header)
        rewritten = self.client.patch(url, {"reason": "something else"}, format="json", **header)
        deleted = self.client.delete(url, **header)

        self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.data)
        self.assertEqual(rewritten.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(deleted.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        referral = Referral.objects.get()
        self.assertEqual((referral.status, referral.reason), ("Accepted", "Persistent chest pain"))
