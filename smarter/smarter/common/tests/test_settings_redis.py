"""
Test that every Redis client survives a Redis restart: the cache, the Celery broker and RedBeat.

Issues #940 and #941: after Redis moved to another node, the workers took no task, Beat crashed, and
requests answered 500 on stale pooled connections, because no client checked its connections.
"""

from django.conf import settings

from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.settings.base import REDIS_HEALTH_CHECK_INTERVAL


class TestRedisSettings(SmarterTestBase):
    """Test the Redis options of the running settings."""

    def test_cache_connections_are_health_checked(self):
        for alias in ("default", "sessions"):
            with self.subTest(alias=alias):
                pool = settings.CACHES[alias]["OPTIONS"]["CONNECTION_POOL_KWARGS"]
                self.assertEqual(pool["health_check_interval"], REDIS_HEALTH_CHECK_INTERVAL)
                self.assertTrue(pool["socket_keepalive"])

    def test_broker_and_redbeat_reconnect(self):
        """A socket timeout above BRPOP's 1 second, keepalive and a health check, for the broker and RedBeat."""
        for options in (settings.CELERY_BROKER_TRANSPORT_OPTIONS, settings.CELERY_REDBEAT_REDIS_OPTIONS):
            with self.subTest(options=options):
                self.assertGreater(options["socket_timeout"], 1)
                self.assertTrue(options["socket_keepalive"])
                self.assertEqual(options["health_check_interval"], REDIS_HEALTH_CHECK_INTERVAL)

    def test_celery_app_uses_the_broker_options(self):
        # pylint: disable=import-outside-toplevel
        from smarter.lib.celery_conf import APP

        self.assertEqual(APP.conf.broker_transport_options, settings.CELERY_BROKER_TRANSPORT_OPTIONS)
        self.assertEqual(APP.conf.redbeat_redis_options, settings.CELERY_REDBEAT_REDIS_OPTIONS)
