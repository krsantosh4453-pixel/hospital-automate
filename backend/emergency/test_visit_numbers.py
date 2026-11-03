"""Every ER visit gets its own number from the server; the second one used to fail."""

from django.test import TestCase
from rest_framework.test import APIClient

from emergency.models import EmergencyVisit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class VisitNumberTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic ER Hospital", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Other ER Hospital", is_active=True)
        cls.nurse, _ = make_staff("er_number_nurse", cls.hospital, role=StaffRole.NURSE)
        cls.patients = []
        for i in range(3):
            patient = Patient.objects.create(
                name=f"Synthetic ER Patient {i}", age=30, gender="Male", phone=f"930000000{i}", hospital=cls.hospital
            )
            PatientHospital.objects.create(patient=patient, hospital=cls.hospital, uhid=f"ERN-{i}")
            cls.patients.append(patient)

    def test_registering_several_visits_gives_each_its_own_number(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.nurse)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

        for patient in self.patients:
            response = client.post(
                "/api/emergency/emergency-visits/",
                {"patient": patient.id, "hospital": self.hospital.id, "triage_level": "Urgent"},
                format="json",
            )
            self.assertEqual(response.status_code, 201, response.content)

        visits = EmergencyVisit.objects.order_by("id")
        self.assertEqual([v.visit_number for v in visits], [f"ER-{v.pk}" for v in visits])

    def test_numbers_are_unique_across_hospitals(self):
        other_patient = Patient.objects.create(
            name="Synthetic Other ER", age=30, gender="Male", phone="9300000099", hospital=self.other_hospital
        )
        first = EmergencyVisit.objects.create(patient=self.patients[0], hospital=self.hospital)
        second = EmergencyVisit.objects.create(patient=other_patient, hospital=self.other_hospital)
        self.assertEqual(first.visit_number, f"ER-{first.pk}")
        self.assertEqual(second.visit_number, f"ER-{second.pk}")
        first.refresh_from_db()
        self.assertEqual(first.visit_number, f"ER-{first.pk}")

    def test_an_explicit_number_is_kept_and_saving_again_keeps_it(self):
        visit = EmergencyVisit.objects.create(patient=self.patients[0], hospital=self.hospital, visit_number="ER-IMPORT-7")
        visit.remarks = "updated"
        visit.save()
        visit.refresh_from_db()
        self.assertEqual(visit.visit_number, "ER-IMPORT-7")
