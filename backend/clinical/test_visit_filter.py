"""
?visit=<id> narrows the per-visit clinical lists to that visit (synthetic data only).

The web consultation page and the mobile app ask for one visit's vitals,
notes, diagnoses and service orders with ?visit=; before this filter the
server ignored it and every record of every patient in the doctor's care came
back, shown as if it belonged to the open visit.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import ClinicalNote, Diagnosis, ServiceOrder, VitalSign
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

LISTS = {
    "vitals": "/api/clinical/vitals/",
    "notes": "/api/clinical/clinical-notes/",
    "diagnoses": "/api/clinical/diagnoses/",
    "orders": "/api/clinical/service-orders/",
}


def ids(response):
    body = response.json()
    rows = body["results"] if isinstance(body, dict) and "results" in body else body
    return {row["id"] for row in rows}


class VisitFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Visit Filter A", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Visit Filter B", is_active=True)
        cls.doctor_user, _ = make_staff("vf_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.colleague_user, _ = make_staff("vf_colleague", cls.hospital, role=StaffRole.DOCTOR)
        cls.doctor = Doctor.objects.create(
            hospital=cls.hospital, user=cls.doctor_user, name="Dr Filter", specialization="General",
            phone="9000000801",
        )
        Doctor.objects.create(
            hospital=cls.hospital, user=cls.colleague_user, name="Dr Colleague", specialization="General",
            phone="9000000802",
        )
        cls.patient = Patient.objects.create(
            name="Synthetic Filter Patient", age=40, gender="Female", phone="9000000811", hospital=cls.hospital,
        )
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="S-VF-1")
        cls.first = Visit.objects.create(hospital=cls.hospital, patient=cls.patient, doctor=cls.doctor)
        cls.second = Visit.objects.create(hospital=cls.hospital, patient=cls.patient, doctor=cls.doctor)
        cls.rows = {visit.id: cls.records_for(visit) for visit in (cls.first, cls.second)}

    @classmethod
    def records_for(cls, visit):
        return {
            "vitals": VitalSign.objects.create(visit=visit, systolic_bp=120).id,
            "notes": ClinicalNote.objects.create(visit=visit, doctor=cls.doctor, plan="Synthetic plan").id,
            "diagnoses": Diagnosis.objects.create(visit=visit, name="Synthetic diagnosis").id,
            "orders": ServiceOrder.objects.create(visit=visit, service_name="Synthetic order").id,
        }

    def get(self, user, url, **params):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        return client.get(url, {"hospital": self.hospital.id, **params})

    def test_each_list_returns_only_the_requested_visit(self):
        for kind, url in LISTS.items():
            for visit in (self.first, self.second):
                with self.subTest(kind=kind, visit=visit.id):
                    response = self.get(self.doctor_user, url, visit=visit.id)
                    self.assertEqual(response.status_code, 200, response.content)
                    self.assertEqual(ids(response), {self.rows[visit.id][kind]})

    def test_without_visit_the_list_is_unchanged(self):
        for kind, url in LISTS.items():
            with self.subTest(kind=kind):
                response = self.get(self.doctor_user, url)
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(
                    ids(response), {self.rows[self.first.id][kind], self.rows[self.second.id][kind]},
                )

    def test_a_visit_id_that_is_not_a_number_is_refused(self):
        for kind, url in LISTS.items():
            # "²" passes str.isdigit() but not int(): it must be a 400, not a 500.
            for value in ("abc", "²", "-1"):
                with self.subTest(kind=kind, value=value):
                    self.assertEqual(self.get(self.doctor_user, url, visit=value).status_code, 400)

    def test_the_filter_never_widens_the_care_scope(self):
        # The colleague has no link to this patient: naming the visit returns nothing.
        for kind, url in LISTS.items():
            with self.subTest(kind=kind):
                response = self.get(self.colleague_user, url, visit=self.first.id)
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(ids(response), set())

    def test_the_filter_never_widens_the_hospital_scope(self):
        outsider, _ = make_staff("vf_outsider", self.other_hospital, role=StaffRole.DOCTOR)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(outsider)
        for kind, url in LISTS.items():
            with self.subTest(kind=kind):
                response = client.get(url, {"hospital": self.hospital.id, "visit": self.first.id})
                rows = ids(response) if response.status_code == 200 else set()
                self.assertEqual(rows, set())
