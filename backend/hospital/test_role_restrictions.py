"""Admins narrow a built-in role per module at their hospital; the server enforces it (synthetic data)."""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from hospital.models import Hospital, RoleModuleRestriction
from pharmacy.models import Medicine
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

URL = "/api/hospital/role-restrictions/"


class RoleRestrictionTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Restrict", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Free", is_active=True)
        self.admin, _ = make_staff("rr_admin", self.hospital, role=StaffRole.ADMIN)
        self.pharmacist, _ = make_staff("rr_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.other_pharmacist, _ = make_staff("rr_pharmacist_b", self.other, role=StaffRole.PHARMACIST)
        Medicine.objects.create(name="Synthetic Tab", hospital=self.hospital, quantity=5, price=Decimal("1"))
        Medicine.objects.create(name="Synthetic Tab B", hospital=self.other, quantity=5, price=Decimal("1"))

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def restrict(self, access, user=None, role="Pharmacist", module="Pharmacy"):
        return self.client_for(user or self.admin).post(URL, {"role": role, "module": module, "access": access}, format="json")

    def medicines(self, user, hospital=None):
        return self.client_for(user, hospital).get(f"/api/pharmacy/?hospital={(hospital or self.hospital).id}")

    def add_medicine(self, user):
        return self.client_for(user).post("/api/pharmacy/", {"name": "New", "hospital": self.hospital.id,
                                                               "quantity": 1, "price": "2.00"}, format="json")

    def test_view_only_blocks_writes_and_no_access_blocks_reads(self):
        self.assertEqual(self.add_medicine(self.pharmacist).status_code, 201)
        resp = self.restrict("view")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self.medicines(self.pharmacist).status_code, 200)
        self.assertEqual(self.add_medicine(self.pharmacist).status_code, 403)

        self.client_for(self.admin).patch(f"{URL}{resp.json()['id']}/", {"access": "none"}, format="json")
        self.assertEqual(self.medicines(self.pharmacist).status_code, 403)
        # Another hospital's pharmacist is unaffected; the admin is never restricted.
        self.assertEqual(self.medicines(self.other_pharmacist, self.other).status_code, 200)
        self.assertEqual(self.add_medicine(self.admin).status_code, 201)

        self.client_for(self.admin).delete(f"{URL}{resp.json()['id']}/")
        self.assertEqual(self.medicines(self.pharmacist).status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="hospital.rolemodulerestriction.delete").exists())

    def test_only_admins_restrict_and_admin_role_cannot_be_restricted(self):
        self.assertEqual(self.restrict("none", user=self.pharmacist).status_code, 403)
        self.assertEqual(self.restrict("none", role="Admin").status_code, 400)
        self.assertEqual(self.restrict("none", module="Users").status_code, 400)
        self.assertEqual(self.restrict("view").status_code, 201)
        self.assertEqual(self.restrict("none").status_code, 400)  # one rule per role and module
        listed = self.client_for(self.pharmacist).get(URL).json()
        self.assertEqual([(r["role"], r["module"], r["access"]) for r in listed.get("results", listed)],
                         [("Pharmacist", "Pharmacy", "view")])
        self.assertEqual(RoleModuleRestriction.objects.count(), 1)
