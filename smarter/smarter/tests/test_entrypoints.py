"""
Test the deployment entry points: the per-environment Django settings modules, the ASGI and WSGI applications, the Celery Beat schedule, and the WebSocket consumers.

None of these are imported by the test runner, which runs under
smarter.settings.local, so these tests import them directly. Importing a
settings module does not reconfigure django.conf.settings, but base_aws.py and
alpha.py extend CORS_ALLOWED_ORIGINS in place, and that list object is shared
with the live settings, so every test restores it.
"""

import importlib
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import async_to_sync

import smarter.settings.base as base_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.unittest.base_classes import SmarterTestBase


def fresh_import(module_name: str):
    """Import a module, or re-execute it if a previous test already imported it."""
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


class TestEnvironmentSettings(SmarterTestBase):
    """Test the settings modules for the AWS-hosted environments."""

    def setUp(self):
        super().setUp()
        self._cors_allowed_origins = list(base_settings.CORS_ALLOWED_ORIGINS)
        self._django_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
        # the settings modules only log their configuration when they are not
        # loaded by manage.py, i.e. when they are loaded by an asgi server.
        argv_patcher = patch.object(sys, "argv", ["uvicorn", "smarter.asgi:application"])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)

    def tearDown(self):
        base_settings.CORS_ALLOWED_ORIGINS[:] = self._cors_allowed_origins
        if self._django_settings_module is not None:
            os.environ["DJANGO_SETTINGS_MODULE"] = self._django_settings_module
        super().tearDown()

    def test_base_aws(self):
        """Base_aws uses redis for caching and celery, mysql, and secure session cookies."""
        module = fresh_import("smarter.settings.base_aws")
        self.assertEqual(module.CACHES["default"]["BACKEND"], "django_redis.cache.RedisCache")
        self.assertEqual(module.SESSION_ENGINE, "django.contrib.sessions.backends.cache")
        self.assertEqual(module.CELERY_REDBEAT_REDIS_URL, module.CELERY_BROKER_URL)
        self.assertEqual(module.CELERY_BEAT_SCHEDULER, "redbeat.RedBeatScheduler")
        self.assertEqual(module.DATABASES["default"]["ENGINE"], "django.db.backends.mysql")
        self.assertTrue(module.SESSION_COOKIE_SECURE)
        self.assertFalse(module.STRIPE_LIVE_MODE)
        self.assertIsNone(module.SECURE_PROXY_SSL_HEADER)
        self.assertTrue(all(origin.startswith("https://") for origin in module.CSRF_TRUSTED_ORIGINS))
        self.assertIn(f"https://{module.ENVIRONMENT_DOMAIN}", module.CORS_ALLOWED_ORIGINS)
        self.assertIn("CACHES", module.__all__)
        self.assertNotIn("logger", module.__all__)

    def _assert_environment(self, environment: str, domain_fragment: str):
        module = fresh_import(f"smarter.settings.{environment}")
        self.assertEqual(module.environment_name, environment)
        self.assertTrue(module.SOCIAL_AUTH_REDIRECT_IS_HTTPS)
        self.assertEqual(len(module.CORS_ALLOWED_ORIGIN_REGEXES), 3)
        self.assertTrue(any(domain_fragment in regex for regex in module.CORS_ALLOWED_ORIGIN_REGEXES))
        self.assertIn("CORS_ALLOWED_ORIGIN_REGEXES", module.__all__)
        return module

    def test_alpha(self):
        """Alpha also allows the local react dev server."""
        module = self._assert_environment(SmarterEnvironments.ALPHA, r"\.alpha\.")
        self.assertIn("http://localhost:3000", module.CORS_ALLOWED_ORIGINS)

    def test_beta(self):
        self._assert_environment(SmarterEnvironments.BETA, r"\.platform\.smarter\.sh")

    def test_next(self):
        self._assert_environment(SmarterEnvironments.NEXT, r"\.next\.")

    def test_prod(self):
        self._assert_environment(SmarterEnvironments.PROD, r"\.platform\.smarter\.sh")


class TestBaseSettings(SmarterTestBase):
    """Test smarter.settings.base: environment variable overrides and diagnostics."""

    def test_smart_cast(self):
        """Smart_cast casts a string to the type of the default value."""
        smart_cast = base_settings.smart_cast
        self.assertIs(smart_cast("yes", False), True)
        self.assertIs(smart_cast("0", True), False)
        self.assertEqual(smart_cast("42", 1), 42)
        self.assertEqual(smart_cast("forty-two", 1), 1)
        self.assertEqual(smart_cast("1.5", 1.0), 1.5)
        self.assertEqual(smart_cast("not-a-float", 1.0), 1.0)
        self.assertEqual(smart_cast("['a', 'b']", []), ["a", "b"])
        self.assertEqual(smart_cast("a, b,,c", []), ["a", "b", "c"])
        self.assertEqual(smart_cast("{'a': 1}", {}), {"a": 1})
        self.assertEqual(smart_cast("not a dict", {"default": True}), {"default": True})
        self.assertEqual(smart_cast("['not', 'a', 'dict']", {"default": True}), {"default": True})
        self.assertEqual(smart_cast("text", "default"), "text")

    def _reload_preserving(self, module_name: str):
        """Re-execute a settings module, then put its original namespace back."""
        module = sys.modules[module_name]
        saved = dict(vars(module))
        try:
            return dict(vars(importlib.reload(module)))
        finally:
            vars(module).clear()
            vars(module).update(saved)

    def test_environment_overrides_and_diagnostics(self):
        """
        DJANGO_* environment variables override existing settings, cast to the existing type, or create new settings with an inferred type.

        Outside of manage.py, base.py also logs container diagnostics.
        """
        environ = {
            "DJANGO_APPEND_SLASH": "false",
            "DJANGO_SECRET_KEY": "not-a-real-secret",
            "DJANGO_SMARTER_TEST_LITERAL": "[1, 2]",
            "DJANGO_SMARTER_TEST_VERSION": "1.2.3",
            "DJANGO_SMARTER_TEST_LIST": "a, b",
            "DJANGO_SMARTER_TEST_DICT": "{not: json}",
            "DJANGO_SMARTER_TEST_STR": "hello",
        }
        with (
            patch.dict(os.environ, environ),
            patch.object(sys, "argv", ["uvicorn", "smarter.asgi:application"]),
            patch("logging.config.dictConfig"),
        ):
            namespace = self._reload_preserving("smarter.settings.base")
        self.assertIs(namespace["APPEND_SLASH"], False)
        self.assertEqual(namespace["SECRET_KEY"], "not-a-real-secret")
        self.assertEqual(namespace["SMARTER_TEST_LITERAL"], [1, 2])
        self.assertEqual(namespace["SMARTER_TEST_VERSION"], "1.2.3")
        self.assertEqual(namespace["SMARTER_TEST_LIST"], ["a", "b"])
        self.assertEqual(namespace["SMARTER_TEST_DICT"], "{not: json}")
        self.assertEqual(namespace["SMARTER_TEST_STR"], "hello")
        # the live module is untouched
        self.assertNotIn("SMARTER_TEST_STR", vars(base_settings))

    def test_local_settings_diagnostics(self):
        """Local.py logs its configuration outside of manage.py."""
        with patch.object(sys, "argv", ["uvicorn", "smarter.asgi:application"]):
            namespace = self._reload_preserving("smarter.settings.local")
        self.assertEqual(namespace["environment_name"], "local")


class TestApplicationEntryPoints(SmarterTestBase):
    """Test the ASGI and WSGI applications and the Celery Beat schedule."""

    def setUp(self):
        super().setUp()
        self._django_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")

    def tearDown(self):
        if self._django_settings_module is not None:
            os.environ["DJANGO_SETTINGS_MODULE"] = self._django_settings_module
        super().tearDown()

    def test_asgi_application(self):
        """Asgi routes http and websocket traffic."""
        module = fresh_import("smarter.asgi")
        self.assertIn("http", module.application.application_mapping)
        self.assertIn("websocket", module.application.application_mapping)
        self.assertEqual(module.__all__, ["application"])

    def test_wsgi_application(self):
        """Wsgi wraps the django application with WhiteNoise."""
        module = fresh_import("smarter.wsgi")
        self.assertEqual(type(module.application).__name__, "WhiteNoise")
        self.assertEqual(module.__all__, ["application"])

    def test_celerybeat_schedule(self):
        """Celerybeat routes infrastructure tasks to the infrastructure queue."""
        from smarter.lib.celery_conf import APP

        saved_schedule = APP.conf.beat_schedule
        saved_filename = APP.conf.beat_schedule_filename
        try:
            module = fresh_import("smarter.workers.celerybeat")
            schedule = module.app.conf.beat_schedule
            self.assertIn("aggregate-prompt-history", schedule)
            self.assertEqual(schedule["refresh-llmhost-status"]["options"], module.INFRASTRUCTURE)
            self.assertEqual(schedule["aggregate-charges"]["options"], module.OPERATIONAL)
            for entry in schedule.values():
                self.assertTrue(entry["task"].startswith("smarter.apps."))
        finally:
            APP.conf.beat_schedule = saved_schedule
            APP.conf.beat_schedule_filename = saved_filename


class TestWebSocketConsumers(SmarterTestBase):
    """Test the WebSocket routing and the terminal emulator log consumer."""

    def test_consumers_urlpatterns(self):
        from smarter import consumers

        self.assertIsInstance(consumers.urlpatterns, list)
        self.assertEqual(consumers.__all__, ["urlpatterns"])

    def test_redis_log_consumer_connect_accepts(self):
        """The consumer accepts every connection."""
        from smarter.apps.dashboard.views.terminal_emulator.api.consumers import (
            RedisLogConsumer,
        )

        consumer = RedisLogConsumer()
        consumer.accept = AsyncMock()
        consumer.scope = MagicMock()
        async_to_sync(consumer.connect)()
        consumer.accept.assert_awaited_once()
