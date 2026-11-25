"""
MF-007 (web audit; remaining work 2026-11-25): doctors pick ordered services
and prescribed medicines from the hospital's own lists. They read names only:
no prices, no stock counts, no writes. Synthetic data only.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import ServicePrice
from config.hospital_time import hospital_today
from hospital.models import Hospital
from pharmacy.models import Medicine
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

SERVICES = "/api/billing/price-list/catalogue/"
FORMULARY = "/api/pharmacy/formulary/"


class OrderingCatalogueTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Catalogue", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Elsewhere", is_active=True)
        today = hospital_today()
        price = lambda hospital, category, name, **extra: ServicePrice.objects.create(
            hospital=hospital, category=category, code=name[:6].upper(), name=name, unit_price=Decimal("100.00"),
            effective_from=extra.pop("since", today - timedelta(days=5)), **extra)
        price(self.hospital, "laboratory", "Complete Blood Count", applies_to="Complete Blood Count")
        price(self.hospital, "imaging", "X-Ray Chest", applies_to="X-Ray Chest")
        price(self.hospital, "procedure", "Dressing")
        price(self.hospital, "consultation", "OPD consultation", applies_to="OPD")
        price(self.hospital, "bed", "General bed")
        price(self.hospital, "procedure", "Old procedure", effective_to=today - timedelta(days=1))
        price(self.other, "laboratory", "Elsewhere test")
        Medicine.objects.create(hospital=self.hospital, name="Synth Paracetamol 500", generic_name="Paracetamol",
                                quantity=20, price=Decimal("2.50"))
        Medicine.objects.create(hospital=self.hospital, name="Synth Paracetamol 500", generic_name="Paracetamol",
                                batch="B2", quantity=5, price=Decimal("2.60"))
        Medicine.objects.create(hospital=self.hospital, name="Synth Amoxicillin 250", quantity=0, price=Decimal("5.00"))
        Medicine.objects.create(hospital=self.other, name="Synth Elsewhere Drug", quantity=9, price=Decimal("1.00"))
        self.doctor, _ = make_staff("cat_doc", self.hospital, role=StaffRole.DOCTOR)

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        return client

    def test_doctor_reads_orderable_services_in_force_without_prices(self):
        response = self.client_for(self.doctor).get(f"{SERVICES}?hospital={self.hospital.pk}")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data, [
            {"name": "Complete Blood Count", "category": "laboratory"},
            {"name": "Dressing", "category": "procedure"},
            {"name": "X-Ray Chest", "category": "imaging"},
        ])

    def test_doctor_reads_medicine_names_once_each_with_availability_only(self):
        response = self.client_for(self.doctor).get(f"{FORMULARY}?hospital={self.hospital.pk}")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data, [
            {"name": "Synth Amoxicillin 250", "generic_name": "", "in_stock": False},
            {"name": "Synth Paracetamol 500", "generic_name": "Paracetamol", "in_stock": True},
        ])

    def test_doctors_still_cannot_read_the_price_list_or_stock(self):
        client = self.client_for(self.doctor)
        self.assertEqual(client.get(f"/api/billing/price-list/?hospital={self.hospital.pk}").status_code, 403)
        self.assertEqual(client.get(f"/api/pharmacy/?hospital={self.hospital.pk}").status_code, 403)

    def test_roles_without_ordering_rights_are_refused(self):
        lab, _ = make_staff("cat_lab", self.hospital, role=StaffRole.LAB_STAFF)
        client = self.client_for(lab)
        self.assertEqual(client.get(f"{SERVICES}?hospital={self.hospital.pk}").status_code, 403)
        self.assertEqual(client.get(f"{FORMULARY}?hospital={self.hospital.pk}").status_code, 403)

    def test_a_doctor_in_two_hospitals_reads_only_the_one_asked_for(self):
        from users.models import StaffHospitalMembership
        StaffHospitalMembership.objects.create(staff=self.doctor.staff_profile, hospital=self.other,
                                               role=StaffRole.DOCTOR, is_active=True)
        client = self.client_for(self.doctor)

        services = client.get(f"{SERVICES}?hospital={self.hospital.pk}").data
        medicines = client.get(f"{FORMULARY}?hospital={self.hospital.pk}").data

        self.assertNotIn("Elsewhere test", [row["name"] for row in services])
        self.assertNotIn("Synth Elsewhere Drug", [row["name"] for row in medicines])
