"""Phase 3 tenant context: contexts per hospital, the code-defined permission catalogue, no escalation."""

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from hospital.models import Hospital, RoleModuleRestriction
from patients.models import Patient, PatientHospital
from users.models import PlatformStaff, StaffHospitalMembership, StaffRole
from users.permissions import get_user_roles, user_has_role
from users.role_permissions import ROLE_MODULE_ACTIONS, HasHospitalPermission, permissions_for

from .test_tenant_isolation import make_staff

User = get_user_model()
CONTEXTS = "/api/v1/auth/me/contexts/"


class TenantContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital_a = Hospital.objects.create(name="Synthetic Context A", is_active=True)
        cls.hospital_b = Hospital.objects.create(name="Synthetic Context B", is_active=True)
        cls.suspended = Hospital.objects.create(name="Synthetic Context Suspended", is_active=False)
        cls.user, cls.profile = make_staff("context_staff", cls.hospital_a, role=StaffRole.ADMIN)
        StaffHospitalMembership.objects.create(staff=cls.profile, hospital=cls.hospital_b,
                                               role=StaffRole.RECEPTIONIST)
        StaffHospitalMembership.objects.create(staff=cls.profile, hospital=cls.suspended,
                                               role=StaffRole.HOSPITAL_MANAGER)

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        if hospital is not None:
            client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def test_contexts_list_one_entry_per_active_membership_in_an_active_hospital(self):
        body = self.client_for(self.user).get(CONTEXTS).json()

        self.assertEqual(body["account_type"], "staff")
        by_hospital = {entry["hospital"]["id"]: entry for entry in body["contexts"]}
        self.assertEqual(set(by_hospital), {self.hospital_a.id, self.hospital_b.id})
        self.assertEqual(by_hospital[self.hospital_b.id]["role"], StaffRole.RECEPTIONIST)
        self.assertIn("Patients.Add", by_hospital[self.hospital_b.id]["permissions"])
        self.assertNotIn("Prescriptions.Add", by_hospital[self.hospital_b.id]["permissions"])
        self.assertIsNone(body["platform_role"])

    def test_a_suspended_hospitals_role_counts_nowhere(self):
        self.assertNotIn(StaffRole.HOSPITAL_MANAGER, get_user_roles(self.user))
        self.assertFalse(user_has_role(self.user, StaffRole.HOSPITAL_MANAGER))

    def test_a_role_counts_only_in_its_own_hospital(self):
        self.assertIn("Prescriptions.Add", permissions_for(self.user, self.hospital_a.id))
        self.assertNotIn("Prescriptions.Add", permissions_for(self.user, self.hospital_b.id))
        self.assertEqual(permissions_for(self.user, self.suspended.id), frozenset())

        request = Request(APIRequestFactory().get("/", HTTP_X_HOSPITAL_ID=str(self.hospital_b.id)))
        request.user = self.user
        self.assertFalse(HasHospitalPermission("Prescriptions.Add")().has_permission(request, None))
        self.assertTrue(HasHospitalPermission("Patients.Add")().has_permission(request, None))

    def test_a_restriction_removes_permissions_and_never_adds_any(self):
        RoleModuleRestriction.objects.create(hospital=self.hospital_b, role=StaffRole.RECEPTIONIST,
                                             module="Patients", access=RoleModuleRestriction.VIEW)
        RoleModuleRestriction.objects.create(hospital=self.hospital_b, role=StaffRole.RECEPTIONIST,
                                             module="Prescriptions", access=RoleModuleRestriction.VIEW)

        granted = permissions_for(self.user, self.hospital_b.id)

        self.assertIn("Patients.View", granted)
        self.assertNotIn("Patients.Add", granted)
        self.assertNotIn("Prescriptions.View", granted)  # a restriction cannot grant a module

    def test_a_patient_sees_the_hospitals_they_are_registered_at(self):
        login = User.objects.create_user(username="context_patient")
        patient = Patient.objects.create(user=login, name="Synthetic Context Patient", age=30, gender="Female",
                                         phone="9000000060", hospital=self.hospital_a)
        PatientHospital.objects.create(patient=patient, hospital=self.hospital_a, uhid="CTX-1")

        body = self.client_for(login).get(CONTEXTS).json()

        self.assertEqual(body["account_type"], "patient")
        self.assertEqual([entry["hospital"]["id"] for entry in body["contexts"]], [self.hospital_a.id])

    def test_platform_staff_see_their_platform_role_and_no_hospital_contexts(self):
        operator = User.objects.create_user(username="context_operator")
        PlatformStaff.objects.create(user=operator, role=PlatformStaff.Role.SUPPORT)

        body = self.client_for(operator).get(CONTEXTS).json()

        self.assertEqual((body["platform_role"], body["contexts"]), (PlatformStaff.Role.SUPPORT, []))

    def test_anonymous_callers_get_no_context(self):
        self.assertEqual(APIClient().get(CONTEXTS).status_code, 401)


class RoleEscalationTests(TestCase):
    """Who may hand out which role (Hospital Admin vs Hospital Manager)."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Escalation", is_active=True)
        cls.admin, _ = make_staff("esc_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.manager, _ = make_staff("esc_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.reception, _ = make_staff("esc_reception", cls.hospital, role=StaffRole.RECEPTIONIST)

    def change_role(self, actor, target, role):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(actor)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client.patch(f"/api/v1/users/{target.id}/membership/", {"role": role}, format="json")

    def test_reception_cannot_change_anyones_role(self):
        self.assertEqual(self.change_role(self.reception, self.manager, StaffRole.RECEPTIONIST).status_code, 403)
        self.assertEqual(get_user_roles(self.manager, self.hospital.id), [StaffRole.HOSPITAL_MANAGER])

    def test_a_manager_cannot_change_an_admin(self):
        self.assertEqual(self.change_role(self.manager, self.admin, StaffRole.RECEPTIONIST).status_code, 403)
        self.assertEqual(get_user_roles(self.admin, self.hospital.id), [StaffRole.ADMIN])

    def test_an_admin_of_another_hospital_cannot_change_roles_here(self):
        other = Hospital.objects.create(name="Synthetic Escalation Other", is_active=True)
        outsider, _ = make_staff("esc_outsider", other, role=StaffRole.ADMIN)
        self.assertIn(self.change_role(outsider, self.reception, StaffRole.ADMIN).status_code, (403, 404))
        self.assertEqual(get_user_roles(self.reception, self.hospital.id), [StaffRole.RECEPTIONIST])

    def test_nobody_changes_their_own_role(self):
        self.assertEqual(self.change_role(self.manager, self.manager, StaffRole.ADMIN).status_code, 400)
        self.assertEqual(get_user_roles(self.manager, self.hospital.id), [StaffRole.HOSPITAL_MANAGER])

    def test_a_manager_cannot_make_anyone_admin(self):
        self.assertEqual(self.change_role(self.manager, self.reception, StaffRole.ADMIN).status_code, 403)


class CatalogueMatchesTheWebAppTests(SimpleTestCase):
    """The backend catalogue and the web app's DEFAULT_ROLES must not drift apart."""

    def test_role_module_actions_equal_role_context_jsx(self):
        source = (Path(__file__).resolve().parents[2] / "src/assets/context/RoleContext.jsx").read_text()
        start = source.index("export const DEFAULT_ROLES")
        block = source[start:source.index("\n]", start)]
        frontend = {}
        for chunk in block.split('name: "')[1:]:
            name = chunk[:chunk.index('"')]
            frontend[name] = {module: frozenset(re.findall(r'"(\w+)"', actions))
                              for module, actions in re.findall(r"(\w+): \[([^\]]*)\]", chunk)}
        frontend.pop("Patient", None)

        self.assertEqual(frontend, {role: dict(modules) for role, modules in ROLE_MODULE_ACTIONS.items()})
