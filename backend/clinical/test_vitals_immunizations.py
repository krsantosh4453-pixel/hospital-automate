"""Extended vitals (D2) and the vaccination register (D15)."""

from datetime import timedelta

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from clinical.models import Immunization, VitalSign
from clinical.test_certificates_referrals import make_patient, make_staff, rows
from config.hospital_time import hospital_today
from encounters.models import Visit
from hospital.models import Hospital
from security_tests.test_tenant_isolation import put_in_care
from users.models import StaffRole

VITALS = "/api/clinical/vitals/"
IMMUNIZATIONS = "/api/clinical/immunizations/"


class ClinicalTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="Hospital A", is_active=True)
        self.other_hospital = Hospital.objects.create(name="Hospital B", is_active=True)
        self.patient = make_patient("Asha", "9999999999", self.hospital, "U1")
        self.doctor_user, _ = make_staff("doc_a", self.hospital, StaffRole.DOCTOR)
        put_in_care(self.doctor_user, self.hospital, self.patient)
        self.visit = Visit.objects.filter(patient=self.patient).first()

    def post(self, url, data, user=None, hospital=None):
        self.client.force_authenticate(user=user or self.doctor_user)
        return self.client.post(
            url, data, format="json", HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).pk)
        )


class ExtendedVitalsTests(ClinicalTestBase):
    def test_records_extended_vitals(self):
        response = self.post(VITALS, {
            "visit": self.visit.pk, "pain_score": 6, "gcs": 14, "avpu": "V",
            "head_circumference": "48.50", "muac": "13.20", "urine_output": 350,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        vital = VitalSign.objects.get()
        self.assertEqual((vital.pain_score, vital.gcs, vital.avpu, vital.urine_output), (6, 14, "V", 350))

    def test_rejects_out_of_range_scores(self):
        for field, value in [("pain_score", 11), ("gcs", 2), ("gcs", 16), ("avpu", "X")]:
            with self.subTest(field=field, value=value):
                response = self.post(VITALS, {"visit": self.visit.pk, field: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data["details"])
        self.assertFalse(VitalSign.objects.exists())


class ImmunizationTests(ClinicalTestBase):
    def dose(self, **overrides):
        data = {
            "patient": self.patient.pk,
            "vaccine": "  Hepatitis B ",
            "dose_number": 1,
            "administered_on": str(hospital_today()),
            "route": "IM",
            "next_due_on": str(hospital_today() + timedelta(days=30)),
        }
        data.update(overrides)
        return data

    def test_doctor_records_dose_for_acting_hospital(self):
        response = self.post(IMMUNIZATIONS, self.dose())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        dose = Immunization.objects.get()
        self.assertEqual(dose.vaccine, "Hepatitis B")
        self.assertEqual(dose.hospital, self.hospital)
        self.assertEqual(dose.recorded_by, self.doctor_user)

    def test_rejects_future_dose_and_due_date_before_dose(self):
        future = self.post(IMMUNIZATIONS, self.dose(administered_on=str(hospital_today() + timedelta(days=1)), next_due_on=None))
        backwards = self.post(IMMUNIZATIONS, self.dose(next_due_on=str(hospital_today())))
        blank = self.post(IMMUNIZATIONS, self.dose(vaccine="   "))

        self.assertIn("administered_on", future.data["details"])
        self.assertIn("next_due_on", backwards.data["details"])
        self.assertIn("vaccine", blank.data["details"])
        self.assertFalse(Immunization.objects.exists())

    def test_lists_by_patient_and_hides_other_hospitals(self):
        self.post(IMMUNIZATIONS, self.dose())
        other_patient = make_patient("Ravi", "8888888888", self.other_hospital, "U2")
        Immunization.objects.create(
            hospital=self.other_hospital, patient=other_patient, vaccine="BCG", administered_on=hospital_today()
        )

        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(IMMUNIZATIONS, {"patient": self.patient.pk}, HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertEqual([row["vaccine"] for row in rows(response)], ["Hepatitis B"])

    def test_cannot_record_for_patient_of_another_hospital(self):
        other_patient = make_patient("Ravi", "8888888888", self.other_hospital, "U2")

        response = self.post(IMMUNIZATIONS, self.dose(patient=other_patient.pk))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Immunization.objects.exists())

    def test_doses_cannot_be_deleted(self):
        self.post(IMMUNIZATIONS, self.dose())
        dose = Immunization.objects.get()

        response = self.client.delete(f"{IMMUNIZATIONS}{dose.pk}/", HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Immunization.objects.filter(pk=dose.pk).exists())

    def test_receptionist_cannot_record_doses(self):
        receptionist, _ = make_staff("front", self.hospital, StaffRole.RECEPTIONIST)

        response = self.post(IMMUNIZATIONS, self.dose(), user=receptionist)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AllergyFilterTests(ClinicalTestBase):
    def test_lists_only_the_requested_patients_allergies(self):
        from clinical.models import Allergy

        other = make_patient("Meena", "7777777777", self.hospital, "U3")
        put_in_care(self.doctor_user, self.hospital, other)
        Allergy.objects.create(patient=self.patient, hospital=self.hospital, name="Penicillin", severity="Severe")
        Allergy.objects.create(patient=other, hospital=self.hospital, name="Latex")

        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get("/api/clinical/allergies/", {"patient": self.patient.pk}, HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        self.assertEqual([row["name"] for row in rows(response)], ["Penicillin"])
