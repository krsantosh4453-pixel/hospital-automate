"""F6: the pharmacy's queue of prescriptions to dispense (synthetic data only)."""

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from clinical.models import Prescription, PrescriptionItem
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

URL = "/api/clinical/prescriptions/"
TO_DISPENSE = "Confirmed,Pending,Partially Dispensed"


class PharmacyQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Queue A", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Queue B", is_active=True)
        cls.pharmacist, _ = make_staff("queue_pharm", cls.hospital, role=StaffRole.PHARMACIST)
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, name="Dr Queue Synthetic",
                                           specialization="General", phone="9000009301")
        cls.patient = Patient.objects.create(name="Synthetic Queue Patient", age=33, gender="Male",
                                             phone="9000009302", hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="QA-2026-000007")
        cls.confirmed = cls.rx("Confirmed")
        cls.partial = cls.rx("Partially Dispensed")
        cls.dispensed = cls.rx("Dispensed")
        cls.pending_check = cls.rx("Pending Verification")
        stranger = Patient.objects.create(name="Synthetic Queue Elsewhere", age=33, gender="Male",
                                          phone="9000009303", hospital=cls.other)
        cls.elsewhere = Prescription.objects.create(hospital=cls.other, patient=stranger, status="Confirmed")

    @classmethod
    def rx(cls, status):
        prescription = Prescription.objects.create(hospital=cls.hospital, patient=cls.patient, doctor=cls.doctor,
                                                   status=status)
        PrescriptionItem.objects.create(prescription=prescription, name="Paracetamol", quantity=3,
                                        instructions="After food")
        return prescription

    def get(self, **params):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.pharmacist)
        resp = client.get(URL, {"hospital": self.hospital.id, **params})
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        return data.get("results", data)

    def ids(self, **params):
        return [row["id"] for row in self.get(**params)]

    def test_queue_lists_what_is_still_to_dispense_oldest_first(self):
        self.assertEqual(self.ids(status=TO_DISPENSE, order="oldest"), [self.confirmed.pk, self.partial.pk])

    def test_awaiting_verification_is_its_own_list(self):
        self.assertEqual(self.ids(status="Pending Verification"), [self.pending_check.pk])

    def test_rows_carry_uhid_doctor_and_instructions(self):
        row = self.get(status="Confirmed")[0]
        self.assertEqual((row["patient_uhid"], row["doctor_name"]), ("QA-2026-000007", "Dr Queue Synthetic"))
        self.assertEqual(row["items"][0]["instructions"], "After food")

    def test_search_by_rx_number_uhid_patient_or_doctor(self):
        for text in (f"RX-{self.confirmed.pk:04d}", str(self.confirmed.pk)):
            with self.subTest(text=text):
                self.assertEqual(self.ids(search=text), [self.confirmed.pk])
        everyone = {self.confirmed.pk, self.partial.pk, self.dispensed.pk, self.pending_check.pk}
        for text in ("qa-2026-000007", "queue patient", "Dr Queue"):
            with self.subTest(text=text):
                self.assertEqual(set(self.ids(search=text)), everyone)

    def test_other_hospitals_prescriptions_never_appear(self):
        self.assertNotIn(self.elsewhere.pk, self.ids(status=TO_DISPENSE))
        self.assertNotIn(self.elsewhere.pk, self.ids(search=str(self.elsewhere.pk)))

    def test_queries_do_not_grow_with_the_queue(self):
        self.get(status=TO_DISPENSE)  # the first request also caches who the user is
        with CaptureQueriesContext(connection) as few:
            self.get(status=TO_DISPENSE)
        for _ in range(5):
            self.rx("Confirmed")
        with CaptureQueriesContext(connection) as many:
            self.get(status=TO_DISPENSE)
        self.assertEqual(len(many), len(few))
