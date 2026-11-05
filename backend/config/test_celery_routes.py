"""Every Celery task must land on a queue the compose workers actually consume (RL-08b)."""

import re
from pathlib import Path

from django.test import SimpleTestCase

from config.celery import app

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILES = ("docker-compose.prod.yml", "docker-compose.dev.yml")


def worker_queues(compose_file):
    """Queues named by ``-Q`` on the celery worker command; Celery's default queue if none."""
    text = (REPO_ROOT / compose_file).read_text()
    worker = text.split("celery-worker:", 1)[1].split("celery-beat:", 1)[0]
    match = re.search(r"-Q\s+([\w,]+)", worker)
    return set(match.group(1).split(",")) if match else {"celery"}


class CeleryRoutingTests(SimpleTestCase):
    def setUp(self):
        app.loader.import_default_modules()
        self.tasks = sorted(name for name in app.tasks if not name.startswith("celery."))

    def queue_of(self, name):
        return app.amqp.router.route({}, name, (), {})["queue"].name

    def test_project_tasks_are_registered(self):
        self.assertIn("notifications.tasks.place_voice_call", self.tasks)
        self.assertIn("notifications.tasks.cleanup_expired_otp", self.tasks)

    def test_every_task_goes_to_a_queue_each_worker_consumes(self):
        for compose_file in COMPOSE_FILES:
            consumed = worker_queues(compose_file)
            for name in self.tasks:
                with self.subTest(compose=compose_file, task=name):
                    self.assertIn(self.queue_of(name), consumed)
