"""Public health endpoints: correct status codes, and no internal error text on failure."""

from unittest import mock

from django.test import TestCase

LEAKY_ERROR = 'could not connect to server: host "db-primary.internal" user "hms_prod"'


class HealthEndpointTests(TestCase):
    def test_basic_and_liveness_answer_without_auth(self):
        for path, status in (("/health/", "healthy"), ("/health/live/", "alive")):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], status)

    def test_readiness_is_ready_when_database_and_cache_work(self):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["checks"]["database"], "healthy")
        self.assertEqual(body["checks"]["cache"], "healthy")

    def test_database_failure_is_503_without_the_error_text(self):
        with mock.patch("config.health.connection.cursor", side_effect=Exception(LEAKY_ERROR)), \
                self.assertLogs("config.health", level="ERROR"):
            response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["database"], "unhealthy")
        self.assertNotIn("db-primary", response.content.decode())

    def test_cache_failure_is_503_without_the_error_text(self):
        with mock.patch("config.health.cache.set", side_effect=Exception(LEAKY_ERROR)), \
                self.assertLogs("config.health", level="ERROR"):
            response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["cache"], "unhealthy")
        self.assertNotIn("hms_prod", response.content.decode())

    def test_cache_that_loses_writes_is_503(self):
        with mock.patch("config.health.cache.get", return_value=None):
            response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["cache"], "unhealthy")
