"""Narrow patient lookup used to place walk-in lab orders."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from hospital.models import Hospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

from .models import Patient, PatientHospital

URL = "/api/patients/lookup/"

User = get_user_model()


def staff(username, role, hospital):
    user = User.objects.create_user(username=username, password="x")
    profile = StaffProfile.objects.create(
        user=user, role=role, employee_id=f"EMP-{username}", is_active_staff=True
    )
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user


class PatientLookupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(name="Hospital A", is_active=True)
        self.other = Hospital.objects.create(name="Hospital B", is_active=True)
        self.lab = staff("lab-tech", StaffRole.LAB_STAFF, self.hospital)

        self.ravi = Patient.objects.create(
            name="Ravi Kumar", age=52, gender="Male", phone="9000012345",
            condition="Diabetes", hospital=self.hospital,
        )
        PatientHospital.objects.create(patient=self.ravi, hospital=self.hospital, is_active=True)
        self.elsewhere = Patient.objects.create(
            name="Ravi Shankar", age=40, gender="Male", phone="9000067890", hospital=self.other,
        )
        PatientHospital.objects.create(patient=self.elsewhere, hospital=self.other, is_active=True)

    def _get(self, search, user=None):
        self.client.force_authenticate(user=user or self.lab)
        return self.client.get(URL, {"hospital": self.hospital.pk, "search": search})

    def test_lab_staff_cannot_list_patients(self):
        self.client.force_authenticate(user=self.lab)

        response = self.client.get("/api/patients/", {"hospital": self.hospital.pk})

        self.assertEqual(response.status_code, 403)

    def test_lab_staff_find_a_patient_of_their_hospital(self):
        response = self._get("ravi")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data], [self.ravi.pk])

    def test_only_minimal_fields_and_masked_phone(self):
        row = self._get("ravi").data[0]

        self.assertEqual(set(row), {"id", "name", "age", "gender", "phone"})
        self.assertEqual(row["phone"], "******2345")

    def test_finds_by_phone(self):
        self.assertEqual([r["id"] for r in self._get("12345").data], [self.ravi.pk])

    def test_does_not_match_on_condition(self):
        self.assertEqual(self._get("Diabetes").data, [])

    def test_short_search_is_refused(self):
        self.assertEqual(self._get("ra").status_code, 400)
        self.assertEqual(self._get("").status_code, 400)

    def test_results_are_capped(self):
        for n in range(25):
            p = Patient.objects.create(name=f"Ravi {n}", age=20, gender="Male", phone=f"80000{n:05d}",
                                       hospital=self.hospital)
            PatientHospital.objects.create(patient=p, hospital=self.hospital, is_active=True)

        self.assertEqual(len(self._get("ravi").data), 20)

    def test_lookup_is_audited(self):
        self._get("ravi")

        log = AuditLog.objects.get(action="patients.patient.lookup")
        self.assertEqual(json.loads(log.details)["patient_ids"], [self.ravi.pk])

    def test_store_staff_may_not_look_up(self):
        # Pharmacists may since F13 (paper transcription); see PharmacistLookupTests.
        store = staff("store", StaffRole.INVENTORY_STAFF, self.hospital)

        self.assertEqual(self._get("ravi", user=store).status_code, 403)


class PharmacistLookupTests(PatientLookupTests.__base__):
    """F13: a pharmacist finds the patient named on a paper prescription, but cannot browse patients."""

    def test_pharmacist_uses_the_narrow_lookup_only(self):
        hospital = Hospital.objects.create(name="Hospital P", is_active=True)
        Patient.objects.create(name="Synthetic Paper Lookup", age=30, gender="Male", phone="9000011111",
                               hospital=hospital)
        pharmacist = staff("lookup-pharmacist", StaffRole.PHARMACIST, hospital)
        client = APIClient()
        client.force_authenticate(user=pharmacist)

        found = client.get(URL, {"hospital": hospital.pk, "search": "paper lookup"})
        self.assertEqual(found.status_code, 200, found.data)
        self.assertEqual([row["name"] for row in found.data], ["Synthetic Paper Lookup"])
        self.assertTrue(found.data[0]["phone"].startswith("*"))
        self.assertEqual(client.get("/api/patients/", {"hospital": hospital.pk}).status_code, 403)
