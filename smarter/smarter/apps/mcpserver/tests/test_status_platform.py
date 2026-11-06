"""Test smarter.apps.mcpserver.services.status.platform: the health checks, the Celery queues and the database's load."""

from unittest import mock

from amqp.exceptions import ChannelError

from smarter.apps.mcpserver.services.status import platform
from smarter.apps.mcpserver.services.status.platform import (
    HealthCheckResult,
    as_number,
    database_load,
    health_checks,
    queue_depths,
    task_queues,
)
from smarter.common.conf import smarter_settings
from smarter.lib.unittest.base_classes import SmarterTestBase

CELERY_APP = "smarter.lib.celery_conf.APP"


class TestQueueDepths(SmarterTestBase):
    """Test queue_depths(), with a fake broker connection."""

    def broker(self, declare):
        """A fake Celery app whose broker channel's queue_declare is ``declare``."""
        app = mock.MagicMock()
        connection = app.connection_for_read.return_value.__enter__.return_value
        connection.default_channel.queue_declare.side_effect = declare
        return app

    def test_task_queues(self):
        self.assertEqual(
            task_queues(),
            (
                smarter_settings.llmclient_tasks_celery_task_queue,
                smarter_settings.infrastructure_tasks_celery_task_queue,
            ),
        )

    def test_depths(self):
        def declare(queue, passive):
            self.assertTrue(passive, "a queue is never created")
            if queue == smarter_settings.infrastructure_tasks_celery_task_queue:
                raise RuntimeError("no such queue")
            return mock.Mock(message_count=7)

        with mock.patch(CELERY_APP, self.broker(declare)):
            depths = queue_depths()
        self.assertEqual(depths[smarter_settings.llmclient_tasks_celery_task_queue], 7)
        self.assertIsNone(depths[smarter_settings.infrastructure_tasks_celery_task_queue], "unknown, not empty")

    def test_empty_queue_on_redis(self):
        """Kombu answers a passive declaration of an empty Redis queue with 404, which is a depth of zero."""

        for not_found in ("404", 404):
            with self.subTest(reply_code=not_found):

                def declare(queue, passive, not_found=not_found):
                    if queue == smarter_settings.llmclient_tasks_celery_task_queue:
                        raise ChannelError("NOT_FOUND - no queue", reply_code=not_found)
                    raise ChannelError("ACCESS_REFUSED", reply_code="403")

                with mock.patch(CELERY_APP, self.broker(declare)):
                    depths = queue_depths()
                self.assertEqual(depths[smarter_settings.llmclient_tasks_celery_task_queue], 0)
                self.assertIsNone(
                    depths[smarter_settings.infrastructure_tasks_celery_task_queue], "another refusal is unknown"
                )

    def test_broker_down(self):
        app = mock.MagicMock()
        app.connection_for_read.side_effect = ConnectionError("refused")
        with mock.patch(CELERY_APP, app):
            depths = queue_depths()
        self.assertEqual(set(depths.values()), {None})
        self.assertEqual(len(depths), 2)


class TestDatabaseLoad(SmarterTestBase):
    """Test database_load(), on the test database, which is MariaDB."""

    def test_load(self):
        load = database_load()
        self.assertGreaterEqual(load.connections, 1, "this test's own connection")
        self.assertGreater(load.max_connections, 0)
        self.assertGreaterEqual(load.running, 1)
        self.assertIsNotNone(load.slow_queries)
        self.assertGreater(load.uptime_seconds, 0)

    def test_as_number(self):
        self.assertEqual(as_number("42"), 42)
        self.assertIsNone(as_number(None))
        self.assertIsNone(as_number("ON"))


class TestHealthChecks(SmarterTestBase):
    """Test health_checks(), which runs the dashboard's own checks."""

    def test_health_checks(self):
        results = [
            {"name": "Database", "healthy": True, "error": ""},
            {"name": "Workers", "healthy": False, "error": "TimeoutError: no answer"},
        ]
        with mock.patch(
            "smarter.apps.dashboard.views.views.api.service_health.run_health_checks", return_value=results
        ):
            self.assertEqual(
                health_checks(),
                [HealthCheckResult("Database", True), HealthCheckResult("Workers", False, "TimeoutError: no answer")],
            )

    def test_module_logger(self):
        self.assertTrue(platform.logger_prefix)
