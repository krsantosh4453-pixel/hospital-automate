"""
P2-1 (policy decision 2026-11-25: "Haan, read-only"): Lab Staff may read one
patient's visits to link a lab order to its visit. Only that: no browsing of
all visits, no detail, no writes, no clinical text. Synthetic data only.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

URL = "/api/encounters/visits/"


class LabStaffVisitLookupTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Lab Lookup", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Lookup", is_active=True)
        self.doctor_user, _ = make_staff("llv_doc", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(user=self.doctor_user, hospital=self.hospital, name="Dr Synthetic Lookup",
                                            specialization="General", phone="9000081001")
        self.patient = Patient.objects.create(name="Synthetic Lookup Patient", age=40, gender="Female",
                                              phone="9000081101", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="LLV-1")
        self.visit = Visit.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                          chief_complaint="Private complaint text")
        self.lab, _ = make_staff("llv_lab", self.hospital, role=StaffRole.LAB_STAFF)

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).pk))
        return client

    def test_lab_staff_read_one_patients_visits_without_clinical_text(self):
        response = self.client_for(self.lab).get(f"{URL}?patient={self.patient.pk}")

        self.assertEqual(response.status_code, 200, response.content)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual([row["id"] for row in rows], [self.visit.pk])
        self.assertNotIn("Private complaint text", str(response.data))
        self.assertEqual(set(rows[0]), {"id", "patient", "hospital", "doctor", "doctor_name", "visit_type", "visit_date", "status"})

    def test_lab_staff_cannot_browse_open_or_change_visits(self):
        client = self.client_for(self.lab)
        self.assertEqual(client.get(URL).status_code, 403)
        self.assertEqual(client.get(f"{URL}{self.visit.pk}/").status_code, 403)
        self.assertEqual(client.post(URL, {"hospital": self.hospital.pk, "patient": self.patient.pk}, format="json").status_code, 403)
        self.assertEqual(client.patch(f"{URL}{self.visit.pk}/", {"status": "In Consultation"}, format="json").status_code, 403)

    def test_other_roles_and_hospitals_gain_nothing(self):
        pharmacist, _ = make_staff("llv_ph", self.hospital, role=StaffRole.PHARMACIST)
        self.assertEqual(self.client_for(pharmacist).get(f"{URL}?patient={self.patient.pk}").status_code, 403)
        outsider, _ = make_staff("llv_lab_b", self.other, role=StaffRole.LAB_STAFF)
        rows = self.client_for(outsider, self.other).get(f"{URL}?patient={self.patient.pk}").data
        rows = rows.get("results", rows) if isinstance(rows, dict) else rows
        self.assertEqual(rows, [])
        self.assertEqual(self.client_for(outsider, self.hospital).get(f"{URL}?patient={self.patient.pk}").status_code, 403)

    def test_doctors_still_see_the_full_visit(self):
        rows = self.client_for(self.doctor_user).get(f"{URL}?patient={self.patient.pk}").data
        rows = rows.get("results", rows) if isinstance(rows, dict) else rows
        self.assertEqual(rows[0]["chief_complaint"], "Private complaint text")


class LabStaffOrderLinksVisitTests(LabStaffVisitLookupTests):
    """The point of the lookup: a Lab Staff walk-in order saves with its visit."""

    def test_lab_staff_order_saves_with_the_visit(self):
        payload = {"hospital": self.hospital.pk, "patient": self.patient.pk, "visit": self.visit.pk,
                   "name": "Complete Blood Count", "priority": "Normal"}

        response = self.client_for(self.lab).post("/api/laboratory/", payload, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data["visit"], self.visit.pk)
