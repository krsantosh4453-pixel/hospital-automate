"""
Each staff role can read exactly the modules of its own work (synthetic data).

The menu each role sees (src/assets/context/RoleContext.jsx, locked by
src/__tests__/roleMenus.test.js) follows the same table; the server-only
extras are noted below.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

# One list endpoint per module.
ENDPOINTS = {
    "Patients": "/api/patients/",
    "Appointments": "/api/appointments/",
    "Queue": "/api/encounters/queue-tokens/",
    "Doctors": "/api/doctors/",
    "Nurses": "/api/nurses/nurses/",
    "Prescriptions": "/api/clinical/prescriptions/",
    "Pharmacy": "/api/pharmacy-sales/",
    "Compounders": "/api/compounder/",
    "Laboratory": "/api/laboratory/",
    "Billing": "/api/billing/invoices/",
    "Inventory": "/api/procurement/suppliers/",
    "Medicines": "/api/pharmacy/",
    "BloodBank": "/api/bloodbank/requests/",
    "IPD": "/api/ipd/admissions/",
    "Emergency": "/api/emergency/emergency-visits/",
    "Users": "/api/users/",
}

# Server-only extras: every staff member reads the doctors directory (names
# for dropdowns, no patient data); the Reports page of the front desk counts
# prescriptions; the Inventory page lists medicines.
EXPECTED = {
    StaffRole.DOCTOR: "Patients Appointments Queue Doctors Prescriptions Laboratory BloodBank IPD Emergency",
    StaffRole.NURSE: "Patients Appointments Queue Doctors Nurses Prescriptions Laboratory BloodBank IPD Emergency",
    StaffRole.COMPOUNDER: "Doctors Prescriptions Pharmacy Compounders Inventory Medicines",
    StaffRole.PHARMACIST: "Doctors Prescriptions Pharmacy Compounders Inventory Medicines",
    StaffRole.RECEPTIONIST: "Patients Appointments Queue Doctors Prescriptions Billing",
    StaffRole.LAB_STAFF: "Doctors Laboratory",
    StaffRole.BLOOD_BANK_STAFF: "Doctors BloodBank",
    StaffRole.BILLING_STAFF: "Doctors Billing",
    StaffRole.INVENTORY_STAFF: "Doctors Inventory Medicines",
    StaffRole.HOSPITAL_MANAGER: (
        "Patients Appointments Queue Doctors Nurses Pharmacy Compounders Laboratory Billing "
        "Inventory Medicines BloodBank IPD Emergency Users"
    ),
}

# Hospital Manager oversees clinical work but does not change it.
MANAGER_READ_ONLY = {
    "Patients": {"name": "X", "age": 1, "gender": "Male", "phone": "9000004001"},
    "Laboratory": {"name": "CBC"},
    "IPD": {"reason": "x"},
    "Emergency": {"triage_level": "Emergency"},
}


class RoleAccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Matrix", is_active=True)
        cls.users = {
            role: make_staff(f"matrix_{i}", cls.hospital, role=role)[0] for i, role in enumerate(EXPECTED)
        }

    def client_for(self, role):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.users[role])
        return client

    def test_each_role_reads_exactly_its_own_modules(self):
        mismatches = []
        for role, modules in EXPECTED.items():
            client = self.client_for(role)
            allowed = set(modules.split())
            for module, url in ENDPOINTS.items():
                status = client.get(url, {"hospital": self.hospital.id}).status_code
                if (status < 400) != (module in allowed):
                    mismatches.append(f"{role} {module}: HTTP {status}, expected {'allowed' if module in allowed else 'refused'}")
        self.assertEqual(mismatches, [])

    def test_hospital_manager_cannot_change_clinical_records(self):
        client = self.client_for(StaffRole.HOSPITAL_MANAGER)
        for module, body in MANAGER_READ_ONLY.items():
            resp = client.post(ENDPOINTS[module], {"hospital": self.hospital.id, **body}, format="json")
            self.assertEqual(resp.status_code, 403, module)

    def test_hospital_manager_cannot_read_prescriptions_or_clinical_notes(self):
        client = self.client_for(StaffRole.HOSPITAL_MANAGER)
        for url in ("/api/clinical/prescriptions/", "/api/clinical/clinical-notes/"):
            self.assertEqual(client.get(url, {"hospital": self.hospital.id}).status_code, 403, url)

    def test_nurse_and_compounder_only_read_prescriptions(self):
        for role in (StaffRole.NURSE, StaffRole.COMPOUNDER):
            resp = self.client_for(role).post(
                ENDPOINTS["Prescriptions"], {"hospital": self.hospital.id}, format="json"
            )
            self.assertEqual(resp.status_code, 403, role)
