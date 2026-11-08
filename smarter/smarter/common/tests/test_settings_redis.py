"""
Test that every Redis client survives a Redis restart: the cache, the Celery broker and RedBeat.

Issues #940 and #941: after Redis moved to another node, the workers took no task, Beat crashed, and
requests answered 500 on stale pooled connections, because no client checked its connections.
"""

import warnings

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

    def test_redbeat_finds_its_own_settings(self):
        """
        RedBeat reads its own url and options, without falling back to the broker's (issue #945).

        The fallback is removed in RedBeat 2.5.0, and RedBeat warns when it uses it.
        """
        # pylint: disable=import-outside-toplevel
        from redbeat.schedulers import RedBeatConfig

        from smarter.lib.celery_conf import APP

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            config = RedBeatConfig(APP)

        messages = [str(warning.message) for warning in caught]
        fallback_warnings = [message for message in messages if "RedBeat will stop falling back" in message]
        self.assertEqual(fallback_warnings, [])
        self.assertEqual(config.redis_url, settings.CELERY_REDBEAT_REDIS_URL)
        self.assertEqual(config.redbeat_redis_options, settings.CELERY_REDBEAT_REDIS_OPTIONS)
