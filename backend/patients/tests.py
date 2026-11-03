"""Tests for patients module."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital, PatientDocument
from security_tests.test_tenant_isolation import put_in_care

User = get_user_model()


class PatientAPITests(TestCase):
    """Tests for patient API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="General")

        # Create staff user for Hospital A
        self.user = User.objects.create_user(
            username="doctor_a",
            email="doctor_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.DOCTOR,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.DOCTOR,
            department=self.dept,
            is_active=True,
        )

        # Create patient in Hospital A
        self.patient_a = Patient.objects.create(
            name="Patient A",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient_a,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Create patient in Hospital B
        self.patient_b = Patient.objects.create(
            name="Patient B",
            age=25,
            gender="Female",
            phone="9876543211",
            hospital=self.hospital_b,
        )
        PatientHospital.objects.create(
            patient=self.patient_b,
            hospital=self.hospital_b,
            is_active=True,
        )

        # The acting user is a Doctor: Patient A is in their care.
        put_in_care(self.user, self.hospital_a, self.patient_a)

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_list_url(self):
        return f"/api/patients/?hospital={self.hospital_a.id}"

    def _get_detail_url(self, pk):
        return f"/api/patients/{pk}/?hospital={self.hospital_a.id}"

    def test_list_patients_scoped_to_hospital(self):
        """Test patient list is scoped to user's hospital."""
        response = self.client.get(self._get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        names = [p["name"] for p in data]
        self.assertIn("Patient A", names)
        self.assertNotIn("Patient B", names)

    def test_create_patient_in_hospital(self):
        """Test creating a patient in the user's hospital."""
        response = self.client.post(
            self._get_list_url(),
            {
                "name": "New Patient",
                "age": 40,
                "gender": "Male",
                "phone": "9999999999",
                "hospital": self.hospital_a.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Patient")
        self.assertEqual(response.data["hospital"], self.hospital_a.id)

    def test_cannot_create_patient_in_other_hospital(self):
        """Test cannot create patient in hospital user doesn't belong to."""
        response = self.client.post(
            self._get_list_url(),
            {
                "name": "Cross Patient",
                "age": 35,
                "gender": "Female",
                "phone": "8888888888",
                "hospital": self.hospital_b.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_patient_in_hospital(self):
        """Test retrieving a patient in the user's hospital."""
        response = self.client.get(self._get_detail_url(self.patient_a.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Patient A")

    def test_cannot_retrieve_patient_in_other_hospital(self):
        """Test cannot retrieve patient in another hospital."""
        url = f"/api/patients/{self.patient_b.id}/?hospital={self.hospital_a.id}"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_update_patient(self):
        """Test updating a patient."""
        response = self.client.patch(
            self._get_detail_url(self.patient_a.id),
            {"age": 31, "condition": "Updated condition"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["age"], 31)
        self.patient_a.refresh_from_db()
        self.assertEqual(self.patient_a.age, 31)

    def test_search_finds_patient_by_this_hospitals_uhid(self):
        PatientHospital.objects.filter(patient=self.patient_a).update(uhid="UH-A-001")

        response = self.client.get(f"{self._get_list_url()}&search=uh-a-001")

        ids = [row["id"] for row in response.data.get("results", response.data)]
        self.assertEqual(ids, [self.patient_a.id])

    def test_search_ignores_another_hospitals_uhid(self):
        # Patient A is also registered at B under B's UHID; A's staff must not match on it.
        PatientHospital.objects.create(patient=self.patient_a, hospital=self.hospital_b, uhid="UH-B-777", is_active=True)

        response = self.client.get(f"{self._get_list_url()}&search=UH-B-777")

        self.assertEqual(response.data.get("results", response.data), [])

    def _new_patient(self, phone, **extra):
        data = {"name": "Second Person", "age": 12, "gender": "Female", "phone": phone, "hospital": self.hospital_a.id}
        data.update(extra)
        return self.client.post("/api/patients/", data, format="json")

    def test_registering_a_known_mobile_number_returns_the_match(self):
        response = self._new_patient(self.patient_a.phone)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual([row["id"] for row in response.data["duplicates"]], [self.patient_a.id])
        self.assertFalse(Patient.objects.filter(name="Second Person").exists())

    def test_confirmed_different_person_with_same_number_is_registered(self):
        response = self._new_patient(self.patient_a.phone, confirm_new=True)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_number_known_only_at_another_hospital_is_not_revealed(self):
        response = self._new_patient(self.patient_b.phone)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn("duplicates", response.data)

    def test_demographics_saved(self):
        response = self.client.patch(
            self._get_detail_url(self.patient_a.id),
            {
                "marital_status": "Married", "address_line": "12 MG Road", "city": "Patna",
                "district": "Patna", "state": "Bihar", "pincode": "800001",
                "id_type": "Aadhaar", "id_last4": "4321", "payer_type": "Insurance",
                "payer_name": "Star Health", "policy_number": "SH-77",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.patient_a.refresh_from_db()
        self.assertEqual((self.patient_a.city, self.patient_a.id_last4, self.patient_a.payer_name), ("Patna", "4321", "Star Health"))

    def test_full_id_number_is_refused(self):
        response = self.client.patch(
            self._get_detail_url(self.patient_a.id),
            {"id_type": "Aadhaar", "id_last4": "123456789012"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_last4", response.data["details"])

    def test_demographic_rules(self):
        cases = [
            ({"pincode": "8000"}, "pincode"),
            ({"id_last4": "4321"}, "id_type"),
            ({"payer_type": "Insurance"}, "payer_name"),
            ({"date_of_birth": "2999-01-01"}, "date_of_birth"),
            ({"marital_status": "Unknown"}, "marital_status"),
        ]
        for data, field in cases:
            response = self.client.patch(self._get_detail_url(self.patient_a.id), data, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, data)
            self.assertIn(field, response.data["details"], data)

    def test_emergency_contact_saved_with_digits_only(self):
        response = self.client.patch(
            self._get_detail_url(self.patient_a.id),
            {
                "emergency_contact_name": "Meera",
                "emergency_contact_relation": "Sister",
                "emergency_contact_phone": "+91 98765-43210",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.patient_a.refresh_from_db()
        self.assertEqual(
            (self.patient_a.emergency_contact_name, self.patient_a.emergency_contact_phone),
            ("Meera", "919876543210"),
        )

    def test_emergency_contact_needs_a_phone(self):
        response = self.client.patch(
            self._get_detail_url(self.patient_a.id),
            {"emergency_contact_name": "Meera"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("emergency_contact_phone", response.data["details"])

    def test_emergency_contact_name_change_keeps_stored_phone(self):
        self.patient_a.emergency_contact_phone = "9876543210"
        self.patient_a.save(update_fields=["emergency_contact_phone"])

        response = self.client.patch(
            self._get_detail_url(self.patient_a.id),
            {"emergency_contact_name": "Meera"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_emergency_contact_phone_too_short(self):
        response = self.client.patch(
            self._get_detail_url(self.patient_a.id),
            {"emergency_contact_name": "Meera", "emergency_contact_phone": "12345"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_patient(self):
        """Test deleting a patient."""
        response = self.client.delete(self._get_detail_url(self.patient_a.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(pk=self.patient_a.id).exists())

    def test_patient_hospital_membership(self):
        """Test patient hospital membership functionality."""
        memberships = self.patient_a.hospital_memberships.filter(is_active=True)
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships.first().hospital, self.hospital_a)

    def test_patient_document_upload(self):
        """Test patient document creation."""
        doc = PatientDocument.objects.create(
            patient=self.patient_a,
            title="Lab Report",
            folder="Lab Reports",
            file="documents/test.pdf",
        )
        self.assertEqual(doc.patient, self.patient_a)
        self.assertEqual(doc.title, "Lab Report")


class PatientModelTests(TestCase):
    """Tests for patient model methods and constraints."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Test Hospital", is_active=True)
        self.patient = Patient.objects.create(
            name="Test Patient",
            age=25,
            gender="Female",
            phone="9999999999",
            hospital=self.hospital,
        )

    def test_patient_str(self):
        self.assertEqual(str(self.patient), "Test Patient")

    def test_patient_hospital_membership_unique(self):
        """Test unique constraint on patient-hospital membership."""
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital,
            is_active=True,
            uhid="UHID001",
        )
        with self.assertRaises(Exception):
            PatientHospital.objects.create(
                patient=self.patient,
                hospital=self.hospital,
                is_active=True,
                uhid="UHID002",
            )
