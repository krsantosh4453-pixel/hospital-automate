from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import Prescription
from hospital.models import Hospital
from patients.models import Patient

from .models import Medicine, Sale


def results(response):
    """Unwrap DRF pagination if present."""
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


class PharmacyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A")
        self.hospital_b = Hospital.objects.create(name="Hospital B")

        self.patient = Patient.objects.create(
            name="Test Patient",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )

        self.medicine_a = Medicine.objects.create(
            name="Paracetamol",
            hospital=self.hospital_a,
            category="Tablet",
            batch="PCM1",
            quantity=100,
            price=Decimal("2.50"),
        )
        self.medicine_b = Medicine.objects.create(
            name="Amoxicillin",
            hospital=self.hospital_b,
            category="Capsule",
            batch="AMX1",
            quantity=50,
            price=Decimal("6.00"),
        )

    # 1. Medicine CRUD still works.
    def test_medicine_crud(self):
        # Create
        create = self.client.post(
            "/api/pharmacy/",
            {
                "name": "Azithromycin",
                "hospital": self.hospital_a.id,
                "category": "Tablet",
                "batch": "AZI1",
                "quantity": 25,
                "price": "12.00",
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        medicine_id = create.data["id"]

        # Read
        detail = self.client.get(f"/api/pharmacy/{medicine_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["name"], "Azithromycin")

        # Update
        update = self.client.patch(
            f"/api/pharmacy/{medicine_id}/",
            {"quantity": 40},
            format="json",
        )
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(update.data["quantity"], 40)

        # Delete
        delete = self.client.delete(f"/api/pharmacy/{medicine_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(
            Medicine.objects.filter(pk=medicine_id).exists()
        )

    # 2. Medicine can be filtered by hospital.
    def test_medicine_filter_by_hospital(self):
        response = self.client.get(
            f"/api/pharmacy/?hospital={self.hospital_a.id}"
        )
        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in results(response)]
        self.assertIn("Paracetamol", names)
        self.assertNotIn("Amoxicillin", names)

    # 3. Hospital A cannot receive Hospital B medicine through ?hospital=.
    def test_cannot_assign_medicine_to_other_hospital(self):
        response = self.client.post(
            f"/api/pharmacy/?hospital={self.hospital_a.id}",
            {
                "name": "Cross Hospital",
                "hospital": self.hospital_b.id,
                "quantity": 5,
                "price": "3.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(
            Medicine.objects.filter(name="Cross Hospital").exists()
        )

    # 4. Sale creation succeeds with sufficient stock.
    def test_sale_creation_succeeds(self):
        response = self.client.post(
            "/api/pharmacy-sales/",
            {
                "medicine": self.medicine_a.id,
                "patient_name": "Test Patient",
                "quantity": 10,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Sale.objects.count(), 1)

    # 5. Sale creation deducts stock.
    def test_sale_deducts_stock(self):
        self.client.post(
            "/api/pharmacy-sales/",
            {
                "medicine": self.medicine_a.id,
                "patient_name": "Test Patient",
                "quantity": 30,
            },
            format="json",
        )
        self.medicine_a.refresh_from_db()
        self.assertEqual(self.medicine_a.quantity, 70)

    # 6. Sale total is correct.
    def test_sale_total_is_correct(self):
        response = self.client.post(
            "/api/pharmacy-sales/",
            {
                "medicine": self.medicine_a.id,
                "patient_name": "Test Patient",
                "quantity": 4,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        # 4 * 2.50 = 10.00
        self.assertEqual(Decimal(response.data["total"]), Decimal("10.00"))
        sale = Sale.objects.get(pk=response.data["id"])
        self.assertEqual(sale.unit_price, Decimal("2.50"))
        self.assertEqual(sale.total, Decimal("10.00"))

    # 7. Sale fails when quantity exceeds stock.
    def test_sale_fails_when_quantity_exceeds_stock(self):
        response = self.client.post(
            "/api/pharmacy-sales/",
            {
                "medicine": self.medicine_a.id,
                "patient_name": "Test Patient",
                "quantity": 500,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Sale.objects.count(), 0)

    # 8. Failed sale does not change stock.
    def test_failed_sale_does_not_change_stock(self):
        self.client.post(
            "/api/pharmacy-sales/",
            {
                "medicine": self.medicine_a.id,
                "patient_name": "Test Patient",
                "quantity": 500,
            },
            format="json",
        )
        self.medicine_a.refresh_from_db()
        self.assertEqual(self.medicine_a.quantity, 100)

    # 9. Sale can optionally reference a Prescription.
    def test_sale_can_reference_prescription(self):
        prescription = Prescription.objects.create(
            hospital=self.hospital_a,
            patient=self.patient,
            status="Confirmed",
        )
        response = self.client.post(
            "/api/pharmacy-sales/",
            {
                "medicine": self.medicine_a.id,
                "patient_name": "Test Patient",
                "quantity": 2,
                "prescription": prescription.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        sale = Sale.objects.get(pk=response.data["id"])
        self.assertEqual(sale.prescription_id, prescription.id)

    # 10. Cross-hospital medicine usage is rejected.
    def test_cross_hospital_sale_is_rejected(self):
        response = self.client.post(
            "/api/pharmacy-sales/",
            {
                "medicine": self.medicine_b.id,  # belongs to Hospital B
                "hospital": self.hospital_a.id,  # claimed Hospital A
                "patient_name": "Test Patient",
                "quantity": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Sale.objects.count(), 0)

    # 11. Existing Prescription APIs remain untouched.
    def test_prescription_api_still_works(self):
        Prescription.objects.create(
            hospital=self.hospital_a,
            patient=self.patient,
            status="Confirmed",
        )
        response = self.client.get(
            f"/api/clinical/prescriptions/?hospital={self.hospital_a.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results(response)), 1)
