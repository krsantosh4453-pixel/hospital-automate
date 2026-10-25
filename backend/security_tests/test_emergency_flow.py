"""Emergency visit workflow with staff attribution (synthetic data only)."""

from django.test import TestCase
from rest_framework.test import APIClient

from doctors.models import Doctor
from emergency.models import EmergencyMedication, EmergencyOrder, EmergencyTriage, EmergencyVisit, EmergencyVitals
from hospital.models import Hospital
from nurses.models import Nurse
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff


class EmergencyFlowTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic ER Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other ER Hospital", is_active=True)
        self.user, _ = make_staff("er_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.patient = Patient.objects.create(name="Synthetic ER Patient", age=50, gender="Male", phone="9000000088", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="ER-1")
        self.doctor = Doctor.objects.create(name="Synthetic ER Doctor", specialization="Emergency", phone="9000000089", hospital=self.hospital)
        self.nurse = Nurse.objects.create(name="Synthetic ER Nurse", phone="9000000090", hospital=self.hospital)
        self.foreign_nurse = Nurse.objects.create(name="Synthetic Foreign Nurse", phone="9000000091", hospital=self.other)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def _visit(self):
        response = self.client.post(
            "/api/emergency/emergency-visits/",
            {"patient": self.patient.id, "hospital": self.hospital.id, "triage_level": "Urgent"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return EmergencyVisit.objects.filter(patient=self.patient).latest("id").id

    def url(self, visit_id, action):
        return f"/api/emergency/emergency-visits/{visit_id}/{action}/"

    def test_full_flow_records_staff(self):
        visit = self._visit()
        self.assertEqual(self.client.post(self.url(visit, "start_triage")).status_code, 200)
        r = self.client.post(self.url(visit, "complete_triage"), {"chief_complaint": "Chest pain", "triaged_by": self.nurse.id, "triage_level": "Emergency"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(EmergencyTriage.objects.get(visit_id=visit).triaged_by, self.nurse)

        r = self.client.post(self.url(visit, "start_consultation"), {"doctor_id": self.doctor.id}, format="json")
        self.assertEqual(r.status_code, 200, r.data)

        r = self.client.post(self.url(visit, "add_vitals"), {"heart_rate": 110, "recorded_by": self.nurse.id}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(EmergencyVitals.objects.get(visit_id=visit).recorded_by, self.nurse)

        r = self.client.post(self.url(visit, "add_order"), {"order_type": "Lab", "description": "Troponin", "ordered_by": self.doctor.id}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(EmergencyOrder.objects.get(visit_id=visit).ordered_by, self.doctor)

        r = self.client.post(
            self.url(visit, "add_medication"),
            {"name": "Synthetic drug", "dose": "1 unit", "route": "IV", "frequency": "Once", "prescribed_by": self.doctor.id},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(EmergencyMedication.objects.get(visit_id=visit).prescribed_by, self.doctor)

    def test_staff_ids_from_another_hospital_are_refused(self):
        visit = self._visit()
        self.client.post(self.url(visit, "start_triage"))
        r = self.client.post(self.url(visit, "complete_triage"), {"chief_complaint": "x", "triaged_by": self.foreign_nurse.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(EmergencyTriage.objects.filter(visit_id=visit).exists())

    def test_staff_left_blank_is_allowed(self):
        visit = self._visit()
        self.client.post(self.url(visit, "start_triage"))
        self.client.post(self.url(visit, "complete_triage"), {"chief_complaint": "x"}, format="json")
        self.client.post(self.url(visit, "start_consultation"), {}, format="json")
        r = self.client.post(self.url(visit, "add_vitals"), {"spo2": 97, "recorded_by": ""}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
