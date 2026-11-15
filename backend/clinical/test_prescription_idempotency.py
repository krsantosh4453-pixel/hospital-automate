"""
Idempotency-Key on prescription writes (synthetic data only).

Found by the 2026-11-12 mobile live test: two identical POSTs with the same
Idempotency-Key both answered 201 and wrote two prescriptions, so a network
retry after a lost response gave the patient a duplicate prescription.
"""

import unittest
from unittest import mock

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from clinical.models import Prescription, PrescriptionItem
from clinical.views import PrescriptionViewSet
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_concurrency import run_together
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

URL = "/api/clinical/prescriptions/"
KEY = "3f9a0c1e7b2d4a6f8e1c3b5d7f9a0c2e"


class PrescriptionIdempotencyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Idempotency Hospital", is_active=True)
        cls.doctor_user, _ = make_staff("idem_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.other_user, _ = make_staff("idem_other_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.doctor = Doctor.objects.create(user=cls.doctor_user, hospital=cls.hospital, name="Dr Synthetic Idem",
                                           specialization="General", phone="9000000901")
        Doctor.objects.create(user=cls.other_user, hospital=cls.hospital, name="Dr Synthetic Other",
                              specialization="General", phone="9000000902")
        cls.patient = Patient.objects.create(name="Synthetic Idem Patient", age=35, gender="Female",
                                             phone="9000000903", hospital=cls.hospital)
        put_in_care(cls.doctor_user, cls.hospital, cls.patient)
        put_in_care(cls.other_user, cls.hospital, cls.patient)

    def post(self, body, key=KEY, user=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user or self.doctor_user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key is not None else {}
        return client.post(URL, body, format="json", **headers)

    def body(self, **extra):
        return {"hospital": self.hospital.id, "patient": self.patient.id,
                "items": [{"name": "Paracetamol 500mg", "dosage": "1 tab", "frequency": "TDS",
                           "duration": "3 days", "quantity": 9}], **extra}

    def test_a_retry_with_the_same_key_returns_the_first_prescription(self):
        first = self.post(self.body())
        again = self.post(self.body())
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(again.json()["id"], first.json()["id"])
        self.assertEqual(Prescription.objects.count(), 1)
        self.assertEqual(PrescriptionItem.objects.count(), 1)
        self.assertEqual(Prescription.objects.get().idempotency_key, KEY)

    def test_without_a_key_every_request_still_writes_a_prescription(self):
        self.assertEqual(self.post(self.body(), key=None).status_code, 201)
        self.assertEqual(self.post(self.body(), key=None).status_code, 201)
        self.assertEqual(Prescription.objects.count(), 2)
        self.assertEqual(set(Prescription.objects.values_list("idempotency_key", flat=True)), {""})

    def test_a_new_key_writes_a_new_prescription_even_with_the_same_medicines(self):
        self.assertEqual(self.post(self.body(), key="key-one").status_code, 201)
        self.assertEqual(self.post(self.body(), key="key-two").status_code, 201)
        self.assertEqual(Prescription.objects.count(), 2)

    def test_the_same_key_for_different_medicines_is_refused(self):
        self.assertEqual(self.post(self.body()).status_code, 201)
        changed = self.body(items=[{"name": "Ibuprofen 400mg", "quantity": 6}])
        response = self.post(changed)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(Prescription.objects.count(), 1)
        self.assertEqual(PrescriptionItem.objects.get().name, "Paracetamol 500mg")

    def test_another_doctors_key_is_refused_without_showing_their_prescription(self):
        self.assertEqual(self.post(self.body()).status_code, 201)
        response = self.post(self.body(), user=self.other_user)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertNotIn("id", response.json())
        self.assertNotIn("items", response.json())
        self.assertEqual(Prescription.objects.count(), 1)

    def test_the_same_key_naming_another_doctor_is_refused(self):
        self.assertEqual(self.post(self.body()).status_code, 201)
        other = Doctor.objects.get(user=self.other_user)
        response = self.post(self.body(doctor=other.id))
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(Prescription.objects.count(), 1)

    def test_a_key_is_looked_up_only_in_the_hospital_the_request_writes_to(self):
        # The same key already used at another hospital is neither replayed nor a conflict here.
        elsewhere = Hospital.objects.create(name="Synthetic Idempotency Hospital B", is_active=True)
        Prescription.objects.create(hospital=elsewhere, patient=self.patient, doctor=self.doctor, idempotency_key=KEY)
        response = self.post(self.body())
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Prescription.objects.filter(hospital=self.hospital).count(), 1)

    def test_a_retry_whose_body_is_not_an_object_is_refused_not_a_crash(self):
        self.assertEqual(self.post(self.body()).status_code, 201)
        response = self.post([self.body()])
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(Prescription.objects.count(), 1)

    def test_a_key_of_exactly_80_characters_is_accepted(self):
        key = "k" * 80
        self.assertEqual(self.post(self.body(), key=key).status_code, 201)
        self.assertEqual(self.post(self.body(), key=key).status_code, 200)
        self.assertEqual(Prescription.objects.count(), 1)

    def test_a_key_longer_than_the_column_is_refused(self):
        response = self.post(self.body(), key="k" * 81)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Prescription.objects.exists())

    def test_a_simultaneous_duplicate_is_answered_with_the_first(self):
        # Two requests that both pass the replay check before either has saved:
        # the second save hits the unique constraint and is answered with the first.
        first = self.post(self.body())
        real = PrescriptionViewSet._replay_prescription
        calls = []

        def miss_once(view, key):
            calls.append(key)
            return None if len(calls) == 1 else real(view, key)

        with mock.patch.object(PrescriptionViewSet, "_replay_prescription", autospec=True, side_effect=miss_once):
            racer = self.post(self.body())
        self.assertEqual(len(calls), 2, "the save should have reached the database and been refused")
        self.assertEqual(racer.status_code, 200, racer.content)
        self.assertEqual(racer.json()["id"], first.json()["id"])
        self.assertEqual(Prescription.objects.count(), 1)

    def test_the_database_refuses_a_second_row_with_the_same_key(self):
        Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                    idempotency_key=KEY)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                        idempotency_key=KEY)
        # Blank keys (no header sent) never conflict.
        Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor)
        Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor)
        self.assertEqual(Prescription.objects.count(), 3)


@unittest.skipUnless(connection.vendor == "postgresql", "needs real concurrent writers (set TEST_DATABASE_URL)")
class ParallelPrescriptionTests(TransactionTestCase):
    def test_parallel_requests_with_one_key_write_one_prescription(self):
        hospital = Hospital.objects.create(name="Synthetic Idempotency Race", is_active=True)
        doctor_user, _ = make_staff("idem_race_doctor", hospital, role=StaffRole.DOCTOR)
        Doctor.objects.create(user=doctor_user, hospital=hospital, name="Dr Synthetic Race",
                              specialization="General", phone="9000000911")
        patient = Patient.objects.create(name="Synthetic Race Patient", age=50, gender="Male",
                                         phone="9000000912", hospital=hospital)
        put_in_care(doctor_user, hospital, patient)
        body = {"hospital": hospital.id, "patient": patient.id,
                "items": [{"name": "Paracetamol 500mg", "quantity": 3}]}

        def post(_index):
            client = APIClient(raise_request_exception=False)
            client.force_authenticate(doctor_user)
            client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
            response = client.post(URL, body, format="json", HTTP_IDEMPOTENCY_KEY=KEY)
            return response.status_code, response.json().get("id")

        results = run_together(post)

        self.assertFalse([r for r in results if isinstance(r, Exception)], results)
        statuses = sorted(status for status, _ in results)
        self.assertEqual(statuses.count(201), 1, results)
        self.assertEqual(set(statuses), {200, 201}, results)
        self.assertEqual(len({rx_id for _, rx_id in results}), 1, results)
        self.assertEqual(Prescription.objects.filter(hospital=hospital).count(), 1)
