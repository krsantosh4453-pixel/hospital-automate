"""Analytics endpoints: every KPI and forecast view answers for its own hospital only."""

from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

BASE = "/api/reports/analytics"

KPI_PATHS = [
    "dashboard", "patients", "doctors", "appointments", "queue", "ipd", "emergency",
    "laboratory", "pharmacy", "inventory", "billing", "bloodbank", "ai-scribe",
    "financial", "clinical", "operational", "patient-summary",
]

FORECAST_PATHS = [
    "forecast", "forecast/appointments", "forecast/patients", "forecast/queue",
    "forecast/laboratory", "forecast/medicine", "forecast/beds", "forecast/emergency",
    "forecast/revenue",
]


class AnalyticsViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Analytics Hospital", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        cls.admin, _ = make_staff("analytics_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.outsider, _ = make_staff("analytics_outsider", cls.other_hospital, role=StaffRole.ADMIN)

    def api(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        return client

    def test_every_kpi_endpoint_answers_for_a_member_hospital(self):
        client = self.api(self.admin)
        for path in KPI_PATHS:
            with self.subTest(path=path):
                response = client.get(f"{BASE}/{path}/?hospital={self.hospital.id}&period=last_30_days")
                self.assertEqual(response.status_code, 200, response.content)

    def test_every_forecast_endpoint_answers_with_no_history(self):
        client = self.api(self.admin)
        for path in FORECAST_PATHS:
            with self.subTest(path=path):
                response = client.get(f"{BASE}/{path}/?hospital={self.hospital.id}&forecast_days=7")
                self.assertEqual(response.status_code, 200, response.content)

    def test_another_hospitals_staff_is_refused(self):
        client = self.api(self.outsider)
        for path in KPI_PATHS + FORECAST_PATHS:
            with self.subTest(path=path):
                response = client.get(f"{BASE}/{path}/?hospital={self.hospital.id}")
                self.assertEqual(response.status_code, 403, response.content)

    def test_missing_or_malformed_hospital_is_refused(self):
        client = self.api(self.admin)
        for query in ("", "?hospital=abc"):
            with self.subTest(query=query):
                self.assertEqual(client.get(f"{BASE}/dashboard/{query}").status_code, 403)

    def test_anonymous_is_refused(self):
        response = APIClient().get(f"{BASE}/dashboard/?hospital={self.hospital.id}")
        self.assertIn(response.status_code, (401, 403))

    def test_bad_period_is_a_400_not_a_500(self):
        response = self.api(self.admin).get(f"{BASE}/patients/?hospital={self.hospital.id}&period=fortnight")
        self.assertEqual(response.status_code, 400, response.content)

    def test_non_numeric_forecast_days_is_a_400_not_a_500(self):
        client = self.api(self.admin)
        for path in FORECAST_PATHS:
            with self.subTest(path=path):
                response = client.get(f"{BASE}/{path}/?hospital={self.hospital.id}&forecast_days=abc")
                self.assertEqual(response.status_code, 400, response.content)

    def test_forecast_days_is_clamped(self):
        response = self.api(self.admin).get(
            f"{BASE}/forecast/appointments/?hospital={self.hospital.id}&forecast_days=5000"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertLessEqual(len(response.json().get("forecast", [])), 90)
