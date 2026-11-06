"""ICD-10 loading and typeahead search (D6)."""

import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

from .models import ICD10Code
from .views import search_icd10

User = get_user_model()


def cms_order_line(order, code, billable, short, long):
    return f"{order:05d} {code:<7} {billable} {short:<60} {long}\n"


def write_temp(name, text):
    folder = Path(tempfile.mkdtemp())
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


class LoadICD10CommandTests(TestCase):
    def test_bundled_list_loads_and_is_idempotent(self):
        out = StringIO()
        call_command("load_icd10", stdout=out)
        count = ICD10Code.objects.count()
        self.assertGreater(count, 150)
        self.assertEqual(ICD10Code.objects.get(code="E11.9").description,
                         "Type 2 diabetes mellitus without complications")
        call_command("load_icd10", stdout=StringIO())
        self.assertEqual(ICD10Code.objects.count(), count)
        ICD10Code.objects.filter(code="E11.9").update(description="Changed by a full CMS load")
        call_command("load_icd10", "--if-empty", stdout=StringIO())
        self.assertEqual(ICD10Code.objects.get(code="E11.9").description, "Changed by a full CMS load")

    def test_cms_order_file_and_replace(self):
        call_command("load_icd10", stdout=StringIO())
        path = write_temp("icd10cm_order_2026.txt", "".join([
            cms_order_line(1, "A00", 0, "Cholera", "Cholera"),
            cms_order_line(2, "A000", 1, "Cholera due to Vibrio cholerae 01, biovar cholerae",
                           "Cholera due to Vibrio cholerae 01, biovar cholerae"),
            cms_order_line(3, "E119", 1, "Type 2 diabetes mellitus without complications",
                           "Type 2 diabetes mellitus without complications"),
        ]))
        call_command("load_icd10", str(path), "--replace", stdout=StringIO())
        self.assertEqual(sorted(ICD10Code.objects.values_list("code", "billable")),
                         [("A00", False), ("A00.0", True), ("E11.9", True)])

    def test_csv_without_required_columns_is_rejected(self):
        from django.core.management.base import CommandError

        path = write_temp("bad.csv", "name,desc\nX,Y\n")
        with self.assertRaises(CommandError):
            call_command("load_icd10", str(path), stdout=StringIO())


class ICD10SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_icd10", stdout=StringIO())

    def test_code_prefix_ranks_first_and_dot_is_optional(self):
        codes = [row["code"] for row in search_icd10("E11")]
        self.assertTrue(codes and all(code.startswith("E11") for code in codes))
        self.assertEqual(search_icd10("e119")[0]["code"], "E11.9")
        self.assertEqual(search_icd10("E11.9")[0]["code"], "E11.9")

    def test_words_match_in_any_order(self):
        codes = {row["code"] for row in search_icd10("diabetes type 2 hyperglycemia")}
        self.assertEqual(codes, {"E11.65"})
        self.assertIn("I10", {row["code"] for row in search_icd10("hypertension")})

    def test_short_query_returns_nothing(self):
        self.assertEqual(search_icd10("e"), [])
        self.assertEqual(search_icd10("  "), [])

    def test_endpoint_is_staff_only(self):
        hospital = Hospital.objects.create(name="Synthetic ICD Hospital", is_active=True)
        doctor, _ = make_staff("icd_doctor", hospital, role=StaffRole.DOCTOR)
        client = APIClient()
        client.force_authenticate(doctor)
        resp = client.get("/api/terminology/icd10/", {"q": "asthma", "limit": 2})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.json()["results"]), 2)
        self.assertTrue(all("asthma" in r["description"].lower() for r in resp.json()["results"]))

        patient_user = User.objects.create_user(username="icd_patient", password="Synthetic-Pass-123")
        Patient.objects.create(name="Synthetic", age=30, gender="Male", phone="9000000081", user=patient_user)
        patient_client = APIClient()
        patient_client.force_authenticate(patient_user)
        self.assertEqual(patient_client.get("/api/terminology/icd10/", {"q": "asthma"}).status_code, 403)
        self.assertIn(APIClient().get("/api/terminology/icd10/", {"q": "asthma"}).status_code, (401, 403))
