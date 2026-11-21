"""
Test the deployment entry points: the per-environment Django settings modules, the ASGI and WSGI applications, the Celery Beat schedule, and the WebSocket consumers.

None of these are imported by the test runner, which runs under
smarter.settings.local, so these tests import them directly. Importing a
settings module does not reconfigure django.conf.settings, but base_aws.py and
alpha.py extend CORS_ALLOWED_ORIGINS in place, and that list object is shared
with the live settings, so every test restores it.
"""

import ast
import importlib
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from pydantic import SecretStr

import smarter.settings.base as base_settings
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.typing import SmarterDictType
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
        """Base_aws uses redis for caching and celery, mysql, and secure, HttpOnly session cookies."""
        module = fresh_import("smarter.settings.base_aws")
        self.assertEqual(module.CACHES["default"]["BACKEND"], "django_redis.cache.RedisCache")
        self.assertEqual(module.SESSION_ENGINE, "django.contrib.sessions.backends.cache")
        self.assertEqual(module.CELERY_REDBEAT_REDIS_URL, module.CELERY_BROKER_URL)
        self.assertEqual(module.CELERY_BEAT_SCHEDULER, "redbeat.RedBeatScheduler")
        self.assertEqual(module.DATABASES["default"]["ENGINE"], "django.db.backends.mysql")
        self.assertTrue(module.SESSION_COOKIE_SECURE)
        self.assertTrue(module.SESSION_COOKIE_HTTPONLY)
        self.assertIsNone(module.SECURE_PROXY_SSL_HEADER)
        self.assertTrue(all(origin.startswith("https://") for origin in module.CSRF_TRUSTED_ORIGINS))
        self.assertIn(f"https://{module.ENVIRONMENT_DOMAIN}", module.CORS_ALLOWED_ORIGINS)
        self.assertIn("CACHES", module.__all__)
        self.assertNotIn("logger", module.__all__)

    def test_cache_and_broker_use_different_redis_databases(self):
        """The cache's Redis database, which cache.clear() flushes, must not hold the Celery queues."""
        env = {k: v for k, v in os.environ.items() if k not in ("CACHES_LOCATION", "CELERY_BROKER_URL")}
        with patch.dict(os.environ, env, clear=True):
            module = fresh_import("smarter.settings.base_aws")
        self.assertTrue(module.CACHES["default"]["LOCATION"].endswith(":6379/1"))
        self.assertTrue(module.CELERY_BROKER_URL.endswith(":6379/0"))
        self.assertNotEqual(base_settings.CACHES["default"]["LOCATION"], base_settings.CELERY_BROKER_URL)

    def test_sessions_have_their_own_redis_database(self):
        """Cache.clear() on the default cache must not log users out."""
        env = {k: v for k, v in os.environ.items() if k != "CACHES_LOCATION"}
        env["CACHES_LOCATION"] = "redis://:pw@redis.example.test:6379/1"
        with patch.dict(os.environ, env, clear=True):
            module = fresh_import("smarter.settings.base_aws")
        self.assertEqual(module.SESSION_CACHE_ALIAS, "sessions")
        self.assertEqual(module.CACHES["sessions"]["LOCATION"], "redis://:pw@redis.example.test:6379/2")
        self.assertEqual(base_settings.SESSION_CACHE_ALIAS, "sessions")
        locations = {
            base_settings.CACHES["default"]["LOCATION"],
            base_settings.CACHES["sessions"]["LOCATION"],
            base_settings.CELERY_BROKER_URL,
        }
        self.assertEqual(len(locations), 3)

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
        """Prod allows its own deployed llmclient hosts, and none of another environment's."""
        module = self._assert_environment(SmarterEnvironments.PROD, r"\.platform\.smarter\.sh")
        for environment in (r"\.alpha\.", r"\.beta\.", r"\.next\."):
            self.assertFalse(any(environment in regex for regex in module.CORS_ALLOWED_ORIGIN_REGEXES))
        self.assertTrue(
            any(
                re.match(regex, "https://example.3141-5926-5359.api.smarter.sh")
                for regex in module.CORS_ALLOWED_ORIGIN_REGEXES
            )
        )


ENVIRONMENT_MODULES = ("local", "alpha", "beta", "next", "prod")
"""The settings modules that DJANGO_SETTINGS_MODULE names, one per environment."""


class TestUserSettingsInEveryEnvironment(SmarterTestBase):
    """
    The user's own settings supersede Smarter's in every environment: base.py, base_aws.py and the environment's module.

    Each test re-executes an environment's module, with a user settings file and DJANGO_* variables of its
    own, then restores the module's namespace.
    """

    def setUp(self):
        super().setUp()
        self._cors_allowed_origins = list(base_settings.CORS_ALLOWED_ORIGINS)
        settings_directory = tempfile.TemporaryDirectory()
        self.addCleanup(settings_directory.cleanup)
        self.settings_file = Path(settings_directory.name) / "settings.yaml"
        argv_patcher = patch.object(sys, "argv", ["uvicorn", "smarter.asgi:application"])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)

    def tearDown(self):
        base_settings.CORS_ALLOWED_ORIGINS[:] = self._cors_allowed_origins
        super().tearDown()

    def load(self, environment: str, file_text: str, environ: dict[str, str]) -> SmarterDictType:
        """Re-execute an environment's settings module with this file and these variables, and return its settings."""
        self.settings_file.write_text(file_text, encoding="utf-8")
        variables = {"SMARTER_USER_SETTINGS_FILE": str(self.settings_file), **environ}
        module = sys.modules.get(f"smarter.settings.{environment}")
        saved = dict(vars(module)) if module else None
        try:
            with patch.dict(os.environ, variables):
                return dict(vars(fresh_import(f"smarter.settings.{environment}")))
        finally:
            if module is not None and saved is not None:
                vars(module).clear()
                vars(module).update(saved)

    def test_the_file_supersedes_every_settings_module(self):
        """
        A setting from base.py (APPEND_SLASH), base_aws.py (SESSION_COOKIE_SAMESITE) and the environment's own module.

        local.py sets SESSION_COOKIE_SAMESITE and SESSION_COOKIE_SECURE itself; the AWS environments inherit them
        from base_aws.py.
        """
        file_text = "APPEND_SLASH: false\nSESSION_COOKIE_SAMESITE: Strict\nSESSION_COOKIE_SECURE: false\n"
        for environment in ENVIRONMENT_MODULES:
            with self.subTest(environment=environment):
                settings = self.load(environment, file_text, {})
                self.assertIs(settings["APPEND_SLASH"], False)
                self.assertEqual(settings["SESSION_COOKIE_SAMESITE"], "Strict")
                self.assertIs(settings["SESSION_COOKIE_SECURE"], False)

    def test_a_variable_supersedes_the_file(self):
        file_text = "SESSION_COOKIE_AGE: 100\n"
        environ = {"DJANGO_SESSION_COOKIE_AGE": "200", "DJANGO_CSRF_COOKIE_SECURE": "true"}
        for environment in ENVIRONMENT_MODULES:
            with self.subTest(environment=environment):
                settings = self.load(environment, file_text, environ)
                self.assertEqual(settings["SESSION_COOKIE_AGE"], 200)
                self.assertIs(settings["CSRF_COOKIE_SECURE"], True)

    def test_the_log_shows_the_values_django_runs_with(self):
        """The environment's module logs its settings after the user's own: here, prod's warning about an insecure cookie."""
        with self.assertLogs("smarter.settings.prod", level=logging.DEBUG) as captured:
            self.load("prod", "", {"DJANGO_SESSION_COOKIE_SECURE": "false"})
        messages = [record.getMessage() for record in captured.records]
        self.assertTrue([message for message in messages if message.endswith("SESSION_COOKIE_SECURE: False")])
        self.assertTrue([message for message in messages if "SESSION_COOKIE_SECURE should be set to True" in message])

    def test_no_setting_is_assigned_after_the_user_settings(self):
        """In each environment's module, apply_user_settings() comes after every assignment of a setting."""
        for environment in ENVIRONMENT_MODULES:
            with self.subTest(environment=environment):
                path = Path(base_settings.__file__).parent / f"{environment}.py"
                tree = ast.parse(path.read_text(encoding="utf-8"))
                statements = tree.body
                call_index = None
                for index, statement in enumerate(statements):
                    if ast.unparse(statement) == "apply_user_settings(globals())":
                        call_index = index
                self.assertIsNotNone(call_index, f"{path.name} doesn't call apply_user_settings(globals()).")
                assert call_index is not None
                self.assertEqual(ast.unparse(statements[call_index + 1]), "log_settings_diagnostics(globals())")
                for statement in statements[call_index + 1 :]:
                    self.assertEqual(settings_assigned_in(statement), [], f"{path.name} sets a setting after them.")


SEQUENCE_MUTATORS = ("append", "extend", "insert", "update", "setdefault", "pop", "remove", "clear")
"""The methods of a list or dict that change a setting in place."""


def settings_assigned_in(statement: ast.stmt) -> list[str]:
    """Return the upper case names that a statement assigns, or changes in place, anywhere inside it."""
    retval = []
    for node in ast.walk(statement):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for target in targets:
            while isinstance(target, (ast.Subscript, ast.Attribute)):
                target = target.value
            if isinstance(target, ast.Name) and target.id.isupper():
                retval.append(target.id)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if node.func.attr in SEQUENCE_MUTATORS and isinstance(owner, ast.Name) and owner.id.isupper():
                retval.append(owner.id)
    return retval


class TestBaseSettings(SmarterTestBase):
    """Test smarter.settings.base: environment variable overrides and diagnostics."""

    def _reload_preserving(self, module_name: str):
        """Re-execute a settings module, then put its original namespace back."""
        module = sys.modules[module_name]
        saved = dict(vars(module))
        try:
            return dict(vars(importlib.reload(module)))
        finally:
            vars(module).clear()
            vars(module).update(saved)

    def _reload_base_with_secret_key(self, secret_key: str) -> tuple[SmarterDictType, list[str]]:
        """Re-execute base.py with the given smarter_settings.secret_key, capturing every log message it emits."""
        with (
            patch.dict(os.environ),
            patch.object(sys, "argv", ["uvicorn", "smarter.asgi:application"]),
            patch(
                "smarter.common.conf.smarter_settings",
                smarter_settings.model_copy(update={"secret_key": SecretStr(secret_key)}),
            ),
            patch("logging.config.dictConfig"),
            self.assertLogs("smarter.settings.base", level=logging.DEBUG) as captured,
        ):
            os.environ.pop("DJANGO_SECRET_KEY", None)
            namespace = self._reload_preserving("smarter.settings.base")
        return namespace, [record.getMessage() for record in captured.records]

    def test_configured_secret_key_is_never_logged(self):
        """A SECRET_KEY from smarter_settings is used as is, and its value never appears in a log message."""
        secret_key = f"unit-test-secret-key-{self.hash_suffix}"
        namespace, messages = self._reload_base_with_secret_key(secret_key)
        self.assertEqual(namespace["SECRET_KEY"], secret_key)
        self.assertFalse([message for message in messages if secret_key in message])

    def test_randomized_secret_key_is_never_logged(self):
        """A missing SECRET_KEY is replaced with a random value, with a warning that does not include it."""
        namespace, messages = self._reload_base_with_secret_key(smarter_settings.default_missing_value)
        secret_key = namespace["SECRET_KEY"]
        self.assertNotEqual(secret_key, smarter_settings.default_missing_value)
        self.assertEqual(len(secret_key), 64)
        self.assertTrue(
            [message for message in messages if message.endswith("SECRET_KEY not set. Using a randomized value.")]
        )
        self.assertFalse([message for message in messages if secret_key in message])

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
        """Asgi answers the liveness probe, then routes http and websocket traffic."""
        module = fresh_import("smarter.asgi")
        self.assertEqual(type(module.application).__name__, "HealthzASGIMiddleware")
        self.assertIn("http", module.application.app.application_mapping)
        self.assertIn("websocket", module.application.app.application_mapping)
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
            self.assertEqual(schedule["sync-infrastructure-inventory"]["options"], module.INFRASTRUCTURE)
            self.assertEqual(schedule["aggregate-charges"]["options"], module.OPERATIONAL)
            # beat sends a task by its registered name, which a typo would silently break.
            from smarter.apps.llmclient.tasks import delete_orphan_dns_records

            self.assertEqual(schedule["delete-orphan-dns-records"]["task"], delete_orphan_dns_records.name)
            self.assertEqual(schedule["delete-orphan-dns-records"]["options"], module.INFRASTRUCTURE)
            from smarter.lib.journal.tasks import prune_journal_blobs

            self.assertEqual(schedule["prune-journal-blobs"]["task"], prune_journal_blobs.name)
            self.assertEqual(schedule["prune-journal-blobs"]["options"], module.OPERATIONAL)
            for entry in schedule.values():
                # the tasks of the Django apps, and of the framework's apps in smarter.lib, e.g. the journal.
                self.assertTrue(entry["task"].startswith(("smarter.apps.", "smarter.lib.")))
        finally:
            APP.conf.beat_schedule = saved_schedule
            APP.conf.beat_schedule_filename = saved_filename


class TestWebSocketConsumers(SmarterTestBase):
    """Test the WebSocket routing."""

    def test_consumers_urlpatterns(self):
        from smarter import consumers

        self.assertIsInstance(consumers.urlpatterns, list)
        self.assertEqual(consumers.__all__, ["urlpatterns"])

    def test_the_terminal_is_routed(self):
        """The terminal's WebSocket is at ws/terminal/.

        Its consumer is tested in the dashboard app.
        """
        from smarter import consumers
        from smarter.apps.dashboard.views.terminal_emulator.api.consumers import (
            TerminalConsumer,
        )

        routes = {str(pattern.pattern): pattern.callback for pattern in consumers.urlpatterns}
        self.assertIn("ws/terminal/", routes)
        self.assertIs(routes["ws/terminal/"].consumer_class, TerminalConsumer)
