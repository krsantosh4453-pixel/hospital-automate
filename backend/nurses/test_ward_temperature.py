"""
Prompt 4 (E2E audit BUG-005 / INT-001): ward vitals a nurse records must reach
the doctor, and a temperature must never travel without its unit.
Synthetic data only.
"""
from django.test import TestCase

from hospital.models import Hospital
from nurses.models import NursingAssessment
from security_tests.test_nursing_authorship import WardSetup
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole


class WardTemperatureTests(WardSetup, TestCase):
    def record(self, vitals, user=None):
        return self.client_for(user or self.nurse_user).post("/api/nurses/assessments/", {
            "hospital": self.hospital.id, "patient": self.patient.id, "admission": self.admission.id,
            "assessment_type": "Focused", "vitals": vitals,
        }, format="json")

    def test_a_temperature_is_stored_with_its_unit(self):
        response = self.record({"temperature": "98.6", "temperature_unit": "F", "pulse": "72"})

        self.assertEqual(response.status_code, 201, response.content)
        stored = NursingAssessment.objects.get().vitals
        self.assertEqual((stored["temperature"], stored["temperature_unit"]), ("98.6", "F"))

    def test_a_reading_impossible_in_its_unit_is_refused(self):
        # The classic mix-up: a Fahrenheit number labelled Celsius, and the reverse.
        for vitals in ({"temperature": "98.6", "temperature_unit": "C"},
                       {"temperature": "37.0", "temperature_unit": "F"},
                       {"temperature": "37.0", "temperature_unit": "K"}):
            with self.subTest(vitals=vitals):
                self.assertEqual(self.record(vitals).status_code, 400)
        self.assertFalse(NursingAssessment.objects.exists())

    def test_legitimate_extremes_are_accepted(self):
        for vitals in ({"temperature": "32.5", "temperature_unit": "C"},   # hypothermia
                       {"temperature": "42.1", "temperature_unit": "C"},   # hyperpyrexia
                       {"temperature": "95.0", "temperature_unit": "F"}):
            with self.subTest(vitals=vitals):
                self.assertEqual(self.record(vitals).status_code, 201)

    def test_a_reading_without_a_unit_is_kept_exactly_as_sent(self):
        # Older readings and other clients send no unit: never guessed or converted.
        self.assertEqual(self.record({"temperature": "98.6"}).status_code, 201)
        self.assertEqual(NursingAssessment.objects.get().vitals, {"temperature": "98.6"})

    def test_the_doctor_sees_the_nurses_vitals_with_who_and_when(self):
        self.record({"temperature": "37.4", "temperature_unit": "C", "bp": "118/76"})
        url = f"/api/nurses/assessments/?patient={self.patient.id}"

        # Clinical records are for patients in the clinician's care (existing rule).
        before = self.client_for(self.doctor_user).get(url).json()
        self.assertEqual(before["results"] if isinstance(before, dict) else before, [])
        put_in_care(self.doctor_user, self.hospital, self.patient)

        rows = self.client_for(self.doctor_user).get(url).json()
        rows = rows["results"] if isinstance(rows, dict) else rows

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["vitals"]["temperature_unit"], "C")
        self.assertEqual(rows[0]["nurse_name"], "Synthetic Nurse A")
        self.assertTrue(rows[0]["assessed_at"])

    def test_other_roles_and_other_hospitals_cannot_read_ward_vitals(self):
        self.record({"temperature": "37.4", "temperature_unit": "C"})
        for role in (StaffRole.PHARMACIST, StaffRole.LAB_STAFF, StaffRole.BILLING_STAFF):
            user, _ = make_staff(f"wt_{role.lower().replace(' ', '_')}", self.hospital, role=role)
            with self.subTest(role=role):
                self.assertEqual(self.client_for(user).get("/api/nurses/assessments/").status_code, 403)

        elsewhere = Hospital.objects.create(name="Synthetic Elsewhere", is_active=True)
        outsider, _ = make_staff("wt_other_doctor", elsewhere, role=StaffRole.DOCTOR)
        client = self.client_for(outsider)
        client.credentials(HTTP_X_HOSPITAL_ID=str(elsewhere.id))
        rows = client.get(f"/api/nurses/assessments/?patient={self.patient.id}").json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        self.assertEqual(rows, [])
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        self.assertEqual(client.get("/api/nurses/assessments/").status_code, 403)
