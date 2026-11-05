"""F4: a prescription written from a consultation belongs to that visit, its patient and its doctor."""

from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import Prescription
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

URL = "/api/clinical/prescriptions/"


class ConsultationPrescriptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Consult Rx", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Consult Rx Other", is_active=True)
        cls.patient = Patient.objects.create(name="Synthetic Consult", age=45, gender="Female",
                                             phone="9000009401", hospital=cls.hospital)
        cls.second_patient = Patient.objects.create(name="Synthetic Consult Two", age=46, gender="Male",
                                                    phone="9000009402", hospital=cls.hospital)
        cls.mine_user, _ = make_staff("consult_rx_mine", cls.hospital, role=StaffRole.DOCTOR)
        cls.theirs_user, _ = make_staff("consult_rx_theirs", cls.hospital, role=StaffRole.DOCTOR)
        cls.admin, _ = make_staff("consult_rx_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.mine = put_in_care(cls.mine_user, cls.hospital, cls.patient, cls.second_patient)
        cls.theirs = put_in_care(cls.theirs_user, cls.hospital, cls.patient)
        cls.my_visit = Visit.objects.filter(patient=cls.patient, doctor=cls.mine).first()
        cls.their_visit = Visit.objects.filter(patient=cls.patient, doctor=cls.theirs).first()

    def post(self, user, visit, patient=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client.post(URL, {
            "hospital": self.hospital.id, "patient": (patient or self.patient).id, "visit": visit.id,
            "items": [{"name": "Paracetamol", "quantity": 3, "instructions": "After food"}],
        }, format="json")

    def test_prescription_from_my_visit_is_signed_by_me_and_linked(self):
        resp = self.post(self.mine_user, self.my_visit)
        self.assertEqual(resp.status_code, 201, resp.content)
        rx = Prescription.objects.get(pk=resp.json()["id"])
        self.assertEqual((rx.visit_id, rx.patient_id, rx.doctor_id, rx.hospital_id),
                         (self.my_visit.id, self.patient.id, self.mine.id, self.hospital.id))

    def test_another_doctors_visit_is_refused(self):
        resp = self.post(self.mine_user, self.their_visit)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("visit", resp.json()["details"])
        self.assertFalse(Prescription.objects.exists())

    def test_visit_of_another_patient_is_refused(self):
        resp = self.post(self.mine_user, self.my_visit, patient=self.second_patient)
        self.assertEqual(resp.status_code, 400)

    def test_visit_of_another_hospital_is_refused(self):
        stranger = Patient.objects.create(name="Synthetic Elsewhere", age=30, gender="Male",
                                          phone="9000009403", hospital=self.other_hospital)
        elsewhere = Visit.objects.create(patient=stranger, hospital=self.other_hospital)
        resp = self.post(self.mine_user, elsewhere)
        self.assertIn(resp.status_code, (400, 404))
        self.assertFalse(Prescription.objects.exists())

    def test_admin_may_record_on_any_visit_of_the_hospital(self):
        resp = self.post(self.admin, self.their_visit)
        self.assertEqual(resp.status_code, 201, resp.content)
