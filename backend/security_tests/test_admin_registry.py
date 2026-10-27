"""Every project table can be browsed in Django admin (config/admin_registry.py)."""

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

PROJECT_APPS = [
    "users", "patients", "doctors", "appointments", "nurses", "compounder", "pharmacy",
    "laboratory", "hospital", "encounters", "clinical", "ipd", "emergency", "billing",
    "bloodbank", "notifications", "audit", "procurement", "ai_scribe", "consent",
]


def project_models():
    return [model for app in PROJECT_APPS for model in apps.get_app_config(app).get_models()]


class AdminRegistryTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser("root", "root@example.test", "root-pass-1")
        self.client.force_login(self.superuser)

    def test_every_project_model_is_registered(self):
        missing = [model._meta.label for model in project_models() if not admin.site.is_registered(model)]
        self.assertEqual(missing, [])

    def test_every_changelist_opens(self):
        for model in project_models():
            url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
            self.assertEqual(self.client.get(url).status_code, 200, model._meta.label)

    def test_audit_records_are_read_only(self):
        request = RequestFactory().get("/admin/")
        request.user = self.superuser
        for model in apps.get_app_config("audit").get_models():
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(request), model._meta.label)
            self.assertFalse(model_admin.has_change_permission(request), model._meta.label)
            self.assertFalse(model_admin.has_delete_permission(request), model._meta.label)

    def test_signed_out_visitor_is_sent_to_the_admin_login(self):
        self.client.logout()
        resp = self.client.get(reverse("admin:doctors_doctor_changelist"))
        self.assertEqual(resp.status_code, 302)
