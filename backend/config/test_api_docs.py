"""API docs: the schema must generate, and production keeps it behind a platform-admin sign-in."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

DOC_URLS = ("/api/schema/", "/api/docs/", "/api/redoc/")


class ApiDocsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.platform_admin = get_user_model().objects.create_superuser("docs_root", password="x-Synthetic-1")
        cls.ordinary_user = get_user_model().objects.create_user("docs_user", password="x-Synthetic-1")

    def client_for(self, user=None):
        client = APIClient(raise_request_exception=False)
        if user is not None:
            client.force_authenticate(user)
        return client

    @override_settings(API_DOCS_PUBLIC=False)
    def test_hidden_docs_refuse_anonymous_and_ordinary_users(self):
        for url in DOC_URLS:
            self.assertIn(self.client_for().get(url).status_code, (401, 403), url)
            self.assertEqual(self.client_for(self.ordinary_user).get(url).status_code, 403, url)

    @override_settings(API_DOCS_PUBLIC=False)
    def test_platform_admin_gets_a_generated_schema(self):
        response = self.client_for(self.platform_admin).get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200, response.content[:300])
        paths = response.json()["paths"]
        # Each endpoint is documented once, under the versioned prefix.
        self.assertIn("/api/v1/patients/", paths)
        self.assertNotIn("/api/patients/", paths)
        tags = {tag for item in paths["/api/v1/patients/"].values() for tag in item.get("tags", [])}
        self.assertNotIn("v1", tags)

    @override_settings(API_DOCS_PUBLIC=True)
    def test_public_docs_open_to_anyone(self):
        for url in DOC_URLS:
            self.assertEqual(self.client_for().get(url).status_code, 200, url)
