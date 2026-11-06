"""Dispensing a whole prescription in one step (all medicines or none)."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import Prescription, PrescriptionItem
from config.hospital_time import hospital_today
from hospital.models import Hospital
from patients.models import Patient
from procurement.models import StockTransaction
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

from .models import Medicine, Sale

URL = "/api/pharmacy-sales/dispense-prescription/"

User = get_user_model()


class DispensePrescriptionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="Hospital A")
        self.other_hospital = Hospital.objects.create(name="Hospital B")

        user = User.objects.create_user(username="rx-pharmacist", password="x")
        profile = StaffProfile.objects.create(user=user, role=StaffRole.PHARMACIST, is_active_staff=True)
        StaffHospitalMembership.objects.create(
            staff=profile, hospital=self.hospital, role=StaffRole.PHARMACIST, is_active=True
        )
        self.client.force_authenticate(user=user)

        patient = Patient.objects.create(
            name="Asha Rao", age=40, gender="Female", phone="9876500001", hospital=self.hospital
        )
        self.prescription = Prescription.objects.create(hospital=self.hospital, patient=patient)
        self.item_pcm = PrescriptionItem.objects.create(prescription=self.prescription, name="Paracetamol", quantity=10)
        self.item_amx = PrescriptionItem.objects.create(prescription=self.prescription, name="Amoxicillin", quantity=15)

        self.pcm = Medicine.objects.create(
            name="Paracetamol", hospital=self.hospital, batch="P1", quantity=100, price=Decimal("2.00")
        )
        self.amx = Medicine.objects.create(
            name="amoxicillin", hospital=self.hospital, batch="A1", quantity=20, price=Decimal("5.00")
        )

    def _lines(self, pcm=None, amx=None):
        return [
            {"item": self.item_pcm.pk, "medicine": (pcm or self.pcm).pk},
            {"item": self.item_amx.pk, "medicine": (amx or self.amx).pk},
        ]

    def _post(self, lines, prescription=None):
        return self.client.post(
            URL, {"prescription": (prescription or self.prescription).pk, "lines": lines}, format="json"
        )

    def test_dispenses_every_medicine_and_marks_prescription(self):
        response = self._post(self._lines())

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["sales"]), 2)
        self.pcm.refresh_from_db()
        self.amx.refresh_from_db()
        self.assertEqual(self.pcm.quantity, 90)
        self.assertEqual(self.amx.quantity, 5)
        totals = sorted(Sale.objects.filter(prescription=self.prescription).values_list("total", flat=True))
        self.assertEqual(totals, [Decimal("20.00"), Decimal("75.00")])
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.status, "Dispensed")
        self.assertIsNotNone(self.prescription.dispensed_at)
        self.assertEqual(StockTransaction.objects.filter(reason="Pharmacy sale").count(), 2)

    def test_quantity_comes_from_the_prescription_not_the_client(self):
        lines = [dict(line, quantity=1) for line in self._lines()]
        response = self._post(lines)

        self.assertEqual(response.status_code, 201, response.data)
        self.pcm.refresh_from_db()
        self.assertEqual(self.pcm.quantity, 90)

    def test_short_stock_on_one_line_dispenses_nothing(self):
        Medicine.objects.filter(pk=self.amx.pk).update(quantity=3)

        response = self._post(self._lines())

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("amoxicillin", str(response.data).lower())
        self.pcm.refresh_from_db()
        self.assertEqual(self.pcm.quantity, 100)
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(StockTransaction.objects.exists())
        self.prescription.refresh_from_db()
        self.assertIsNone(self.prescription.dispensed_at)

    def test_every_item_must_be_covered_once(self):
        missing = self._post(self._lines()[:1])
        duplicate = self._post([self._lines()[0], self._lines()[0]])

        self.assertEqual(missing.status_code, 400, missing.data)
        self.assertEqual(duplicate.status_code, 400, duplicate.data)
        self.assertFalse(Sale.objects.exists())

    def test_item_from_another_prescription_is_refused(self):
        other = Prescription.objects.create(hospital=self.hospital, patient=self.prescription.patient)
        stray = PrescriptionItem.objects.create(prescription=other, name="Paracetamol", quantity=1)
        lines = [{"item": stray.pk, "medicine": self.pcm.pk}, self._lines()[1]]

        response = self._post(lines)

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Sale.objects.exists())

    def test_stock_must_be_the_prescribed_medicine(self):
        response = self._post(self._lines(pcm=self.amx, amx=self.pcm))

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Sale.objects.exists())

    def test_expired_batch_is_refused(self):
        Medicine.objects.filter(pk=self.amx.pk).update(expiry_date=hospital_today() - timedelta(days=1))

        response = self._post(self._lines())

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Sale.objects.exists())

    def test_stock_from_another_hospital_is_refused(self):
        foreign = Medicine.objects.create(
            name="Amoxicillin", hospital=self.other_hospital, batch="B1", quantity=50, price=Decimal("5.00")
        )

        response = self._post(self._lines(amx=foreign))

        self.assertEqual(response.status_code, 400, response.data)
        foreign.refresh_from_db()
        self.assertEqual(foreign.quantity, 50)

    def test_second_dispense_is_refused(self):
        first = self._post(self._lines())
        second = self._post(self._lines())

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 409, second.data)
        self.assertEqual(Sale.objects.count(), 2)
        self.pcm.refresh_from_db()
        self.assertEqual(self.pcm.quantity, 90)

    def test_prescription_from_a_hospital_you_do_not_belong_to(self):
        patient = Patient.objects.create(
            name="Other", age=30, gender="Male", phone="9876500002", hospital=self.other_hospital
        )
        foreign_rx = Prescription.objects.create(hospital=self.other_hospital, patient=patient)
        item = PrescriptionItem.objects.create(prescription=foreign_rx, name="Paracetamol", quantity=1)

        response = self._post([{"item": item.pk, "medicine": self.pcm.pk}], prescription=foreign_rx)

        self.assertIn(response.status_code, (403, 404), response.data)
        self.assertFalse(Sale.objects.exists())

    def test_pharmacist_role_in_one_hospital_does_not_dispense_in_another(self):
        """RL-02: Pharmacist in A but only Receptionist in B, acting as A, must not issue B's medicine."""
        profile = StaffProfile.objects.get(user__username="rx-pharmacist")
        StaffHospitalMembership.objects.create(
            staff=profile, hospital=self.other_hospital, role=StaffRole.RECEPTIONIST, is_active=True
        )
        patient = Patient.objects.create(
            name="Other", age=30, gender="Male", phone="9876500003", hospital=self.other_hospital
        )
        foreign_rx = Prescription.objects.create(hospital=self.other_hospital, patient=patient)
        item = PrescriptionItem.objects.create(prescription=foreign_rx, name="Paracetamol", quantity=1)
        stock_b = Medicine.objects.create(
            name="Paracetamol", hospital=self.other_hospital, batch="PB", quantity=10, price=Decimal("2.00")
        )

        response = self.client.post(
            URL, {"prescription": foreign_rx.pk, "lines": [{"item": item.pk, "medicine": stock_b.pk}]},
            format="json", HTTP_X_HOSPITAL_ID=str(self.hospital.id),
        )

        self.assertEqual(response.status_code, 404, response.data)
        self.assertFalse(Sale.objects.exists())
        stock_b.refresh_from_db()
        self.assertEqual(stock_b.quantity, 10)

    def test_prescription_with_no_items_is_refused(self):
        empty = Prescription.objects.create(hospital=self.hospital, patient=self.prescription.patient)

        response = self._post([], prescription=empty)

        self.assertEqual(response.status_code, 400, response.data)
