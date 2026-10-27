"""The seed_demo command builds a synthetic demo hospital for manual testing."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient

DEMO_PASSWORD = "Demo-Check-2026"
User = get_user_model()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def seed(self, *args, **kwargs):
        out = StringIO()
        call_command("seed_demo", *args, stdout=out, **kwargs)
        return out.getvalue()

    def login(self, username):
        client = APIClient()
        resp = client.post("/api/auth/staff/login/", {"username": username, "password": DEMO_PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.json()['access']}")
        return client

    def hospital_id(self):
        return Hospital.objects.get(name="Demo City Hospital").id

    def patient_names(self, username):
        resp = self.login(username).get("/api/patients/", {"hospital": self.hospital_id()})
        body = resp.json()
        return {row["name"] for row in (body["results"] if isinstance(body, dict) else body)}

    def test_creates_every_role_without_printing_the_password(self):
        output = self.seed(password=DEMO_PASSWORD)
        self.assertNotIn(DEMO_PASSWORD, output)
        for username in ("demo.admin", "demo.doctor1", "demo.doctor2", "demo.nurse", "demo.desk", "demo.desk.main",
                         "demo.manager", "demo.pharmacist", "demo.compounder", "demo.lab", "demo.bloodbank",
                         "demo.billing", "demo.inventory"):
            self.assertTrue(User.objects.get(username=username).check_password(DEMO_PASSWORD), username)
        self.assertTrue(Patient.objects.get(user__username="demo.patient").email_verified)

    def test_each_role_sees_what_the_rules_allow(self):
        self.seed(password=DEMO_PASSWORD)
        everyone = self.patient_names("demo.admin")
        self.assertGreaterEqual(len(everyone), 4)
        self.assertEqual(self.patient_names("demo.doctor1"), {"Demo Ravi (Cardiology OPD)", "Demo Kiran (Ward A)"})
        self.assertNotIn("Demo Meena (Ward B)", self.patient_names("demo.nurse"))
        self.assertIn("Demo Kiran (Ward A)", self.patient_names("demo.nurse"))

    def test_running_twice_does_not_duplicate(self):
        self.seed(password=DEMO_PASSWORD)
        count = Patient.objects.count()
        self.seed(password=DEMO_PASSWORD)
        self.assertEqual(Patient.objects.count(), count)

    def test_remove_deletes_only_demo_data(self):
        other = Hospital.objects.create(name="Real Hospital", is_active=True)
        self.seed(password=DEMO_PASSWORD)
        self.seed("--remove")
        self.assertFalse(Hospital.objects.filter(name="Demo City Hospital").exists())
        self.assertFalse(User.objects.filter(username__startswith="demo.").exists())
        self.assertTrue(Hospital.objects.filter(pk=other.pk).exists())

    def test_refuses_a_short_password(self):
        with self.assertRaises(CommandError):
            self.seed(password="short")

    @override_settings(DEBUG=False)
    def test_refuses_to_run_outside_development(self):
        with self.assertRaises(CommandError):
            self.seed(password=DEMO_PASSWORD)
