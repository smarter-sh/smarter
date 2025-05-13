# pylint: disable=wrong-import-position
"""Test User."""

from celery import Celery

# python stuff
from smarter.lib.unittest.base_classes import SmarterTestBase

# our stuff
from smarter.smarter_celery import app


class TestCelery(SmarterTestBase):
    """Test Account model"""

    def setUp(self):
        """Set up test fixtures."""

    def tearDown(self):
        """Clean up test fixtures."""

    def test_celery_is_running(self):
        """Test that Celery is running."""
        try:
            replies = app.control.ping()
            self.assertTrue(replies, "Celery is not running")
        except OSError as e:
            self.fail(f"Celery is not running: {e}")

    def test_celery_configuration(self):
        """Test that the Celery configuration is correct."""
        APP = Celery("smarter")
        APP.conf.task_protocol = 1
        APP.config_from_object("django.conf:settings", namespace="CELERY")
        APP.autodiscover_tasks()

        with APP.connection() as conn:
            conn.ensure_connection(max_retries=3)
