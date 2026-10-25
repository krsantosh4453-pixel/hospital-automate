"""Dashboard statistics endpoints (synthetic data only)."""

from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient

from .test_tenant_isolation import make_staff


class HomeStatsTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Stats Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        self.user, _ = make_staff("stats_admin", self.hospital)
        Patient.objects.create(name="Synthetic Stats Patient", age=40, gender="Male", phone="9000000077", hospital=self.hospital)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)

    def test_summary_endpoint_returns_counts(self):
        # Regression: this view used Sum without importing it (NameError -> 500).
        response = self.client.get(f"/api/home/stats/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["patients"], 1)
        self.assertEqual(response.data["total_revenue"], 0.0)

    def test_detail_endpoint_used_by_dashboard(self):
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["statistics"]["patients"]["total"], 1)
        self.assertEqual(response.data["recent_patients"][0]["name"], "Synthetic Stats Patient")

    def test_other_hospital_is_refused(self):
        for url in ("/api/home/stats/", "/api/home/stats/detail/"):
            response = self.client.get(f"{url}?hospital={self.other.id}")
            self.assertEqual(response.status_code, 403, url)
