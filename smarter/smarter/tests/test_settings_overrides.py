"""Test the deployment's overrides of Django settings: :mod:`smarter.settings.overrides`."""

import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import smarter.settings.overrides as overrides_module
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.settings.overrides import (
    DEFAULT_OVERRIDES_FILE,
    SmarterOverridesError,
    apply_overrides,
    literal_value,
    overrides_file_path,
    overrides_from_environment,
    overrides_from_file,
    value_like,
)

MODULE = "smarter.settings.overrides"

EXAMPLE_LINE = re.compile(r"^# ([A-Z][A-Z0-9_]*:|  )")
"""A commented-out line of an example in settings.example.yaml: a setting, or a line indented under one."""


class TestOverridesFile(SmarterTestBase):
    """The overrides file, in YAML."""

    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "settings.yaml"

    def write(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def test_the_path(self):
        """SMARTER_OVERRIDES_FILE, or its unprefixed name, which wins, as smarter_settings reads them."""
        self.assertEqual(overrides_file_path({}), Path(DEFAULT_OVERRIDES_FILE))
        self.assertEqual(overrides_file_path({"SMARTER_OVERRIDES_FILE": "/a.yaml"}), Path("/a.yaml"))
        both = {"SMARTER_OVERRIDES_FILE": "/a.yaml", "OVERRIDES_FILE": "/b.yaml"}
        self.assertEqual(overrides_file_path(both), Path("/b.yaml"))

    def test_no_file_and_an_empty_file_have_no_settings(self):
        self.assertEqual(overrides_from_file(self.path), {})
        self.assertEqual(overrides_from_file(self.write("")), {})
        self.assertEqual(overrides_from_file(self.write("# only a comment\n")), {})

    def test_nested_values(self):
        text = "SESSION_COOKIE_AGE: 3600\nADMINS:\n  - ops@example.com\nCACHES:\n  default:\n    TIMEOUT: 60\n"
        settings = overrides_from_file(self.write(text))
        self.assertEqual(settings["SESSION_COOKIE_AGE"], 3600)
        self.assertEqual(settings["ADMINS"], ["ops@example.com"])
        self.assertEqual(settings["CACHES"], {"default": {"TIMEOUT": 60}})

    def test_a_file_that_is_not_settings(self):
        for text, error in (
            ("SESSION_COOKIE_AGE: [unclosed\n", "not valid YAML"),
            ("- a list\n", "must be a mapping"),
            ("session_cookie_age: 1\n", "is not a Django setting name"),
            ("1: one\n", "is not a string"),
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(SmarterOverridesError, error):
                    overrides_from_file(self.write(text))


class TestOverridesFromEnvironment(SmarterTestBase):
    """DJANGO_* environment variables, cast to the type of the setting's value before them."""

    def test_literal_value(self):
        self.assertIs(literal_value("true"), True)
        self.assertIs(literal_value("True"), True)
        self.assertEqual(literal_value("5"), 5)
        self.assertEqual(literal_value('{"a": 1}'), {"a": 1})
        self.assertEqual(literal_value("('a', 'b')"), ("a", "b"))
        self.assertEqual(literal_value("1.2.3"), "1.2.3")
        self.assertEqual(literal_value("hello"), "hello")

    def test_value_like_the_current_value(self):
        self.assertIs(value_like("yes", False), True)
        self.assertIs(value_like("0", True), False)
        self.assertEqual(value_like("42", 1), 42)
        self.assertEqual(value_like("1.5", 1.0), 1.5)
        self.assertEqual(value_like("12345", "a string"), "12345")
        self.assertEqual(value_like('["a", "b"]', []), ["a", "b"])
        self.assertEqual(value_like("a, b,,c", []), ["a", "b", "c"])
        self.assertEqual(value_like("a,b", ("x",)), ("a", "b"))
        self.assertEqual(value_like('[("Ops", "ops@example.com")]', []), [("Ops", "ops@example.com")])
        self.assertEqual(value_like('{"a": 1}', {}), {"a": 1})
        self.assertEqual(value_like("('a', 'b')", None), ("a", "b"))

    def test_a_value_of_the_wrong_type(self):
        for text, current in (("forty-two", 1), ("not-a-float", 1.0), ("[1]", {})):
            with self.subTest(text=text):
                with self.assertRaises(SmarterOverridesError):
                    value_like(text, current)

    def test_overrides_from_environment(self):
        environ = {
            "DJANGO_SETTINGS_MODULE": "smarter.settings.local",
            "DJANGO_APPEND_SLASH": "false",
            "DJANGO_session_cookie_age": "60",
            "DJANGO_SMARTER_TEST_NEW": " hello\x07 ",
            "SMARTER_SOMETHING_ELSE": "x",
        }
        current = {"APPEND_SLASH": True, "SESSION_COOKIE_AGE": 1209600}
        settings = overrides_from_environment(environ, current)
        self.assertEqual(settings, {"APPEND_SLASH": False, "SESSION_COOKIE_AGE": 60, "SMARTER_TEST_NEW": "hello"})

    def test_the_secret_key_is_left_to_smarter_settings(self):
        """DJANGO_SECRET_KEY is read, and validated, by smarter_settings.django_secret_key, which base.py's SECRET_KEY is."""
        settings = overrides_from_environment({"DJANGO_SECRET_KEY": "SET-ME-PLEASE"}, {"SECRET_KEY": "generated"})
        self.assertEqual(settings, {})

    def test_the_variables_that_the_helm_chart_sets(self):
        """The chart's and the deploy action's DJANGO_* variables, as lists and strings."""
        backends = "a.Backend,b.Backend"
        broker = "redis://:pw@redis.example.test:6379/0"
        environ = {"DJANGO_AUTHENTICATION_BACKENDS": backends, "DJANGO_CELERY_BROKER_URL": broker}
        current = {"AUTHENTICATION_BACKENDS": ["x.Backend"], "CELERY_BROKER_URL": "redis://smarter-redis:6379/0"}
        settings = overrides_from_environment(environ, current)
        self.assertEqual(settings["AUTHENTICATION_BACKENDS"], ["a.Backend", "b.Backend"])
        self.assertEqual(settings["CELERY_BROKER_URL"], broker)

    def test_django_defaults_give_the_type(self):
        """A setting that Smarter doesn't set takes the type of Django's default: a list for SILENCED_SYSTEM_CHECKS."""
        environ = {"DJANGO_SILENCED_SYSTEM_CHECKS": "security.W001, security.W003"}
        settings = overrides_from_environment(environ, {})
        self.assertEqual(settings["SILENCED_SYSTEM_CHECKS"], ["security.W001", "security.W003"])

    def test_the_example_file(self):
        """Every example in overrides/settings.example.yaml, uncommented, reads as its comments say."""
        # the repository's root on the host, and /home/smarter_user in the containers, where Docker Compose
        # mounts overrides/.
        root = Path(overrides_module.__file__).parents[3]
        example_path = root / "overrides" / "settings.example.yaml"
        if not example_path.is_file():
            self.skipTest("overrides/ isn't mounted here, e.g. in a test shard")
        lines = []
        in_examples = False
        for line in example_path.read_text(encoding="utf-8").splitlines():
            # the examples begin at the first section, below the file's explanation.
            if line.startswith("# --- "):
                in_examples = True
            if not in_examples:
                continue
            if not EXAMPLE_LINE.match(line):
                continue
            if "DJANGO_" in line or line.startswith("#   as a variable") or line.startswith("#   ("):
                continue
            lines.append(line[2:])
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "settings.yaml"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        settings = overrides_from_file(path)
        self.assertEqual(settings["SESSION_COOKIE_AGE"], 3600)
        self.assertEqual(settings["MY_PACKAGE_SAMPLE_RATE"], 0.25)
        self.assertIs(settings["APPEND_SLASH"], False)
        self.assertEqual(settings["MY_PACKAGE_VERSION_LABEL"], "1.10")
        self.assertEqual(settings["MY_PACKAGE_ANSWER"], "no")
        self.assertTrue(str(settings["MY_PACKAGE_BANNER"]).endswith("Activity is logged.\n"))
        self.assertEqual(settings["ADMINS"], ["ops@example.com", "oncall@example.com"])
        self.assertEqual(settings["INTERNAL_IPS"], [])
        self.assertEqual(settings["SECURE_PROXY_SSL_HEADER"], ["HTTP_X_FORWARDED_PROTO", "https"])
        self.assertEqual(settings["LANGUAGES"], [["en", "English"], ["es", "Spanish"]])
        self.assertEqual(settings["MESSAGE_TAGS"], {40: "danger", 30: "warning"})
        self.assertEqual(settings["SECURE_CSP_REPORT_ONLY"]["object-src"], ["'none'"])  # type: ignore[index]
        self.assertEqual(settings["TEST_RUNNER"], "django.test.runner.DiscoverRunner")

    def test_the_example_variables(self):
        """The DJANGO_* forms that the example file's comments give."""
        environ = {
            "DJANGO_SESSION_COOKIE_AGE": "3600",
            "DJANGO_MY_PACKAGE_SAMPLE_RATE": "0.25",
            "DJANGO_SESSION_COOKIE_SECURE": "true",
            "DJANGO_TIME_ZONE": "America/Vancouver",
            "DJANGO_SECURE_PROXY_SSL_HEADER": '("HTTP_X_FORWARDED_PROTO", "https")',
            "DJANGO_SILENCED_SYSTEM_CHECKS": '["security.W001", "security.W003"]',
            "DJANGO_MESSAGE_TAGS": '{40: "danger"}',
        }
        settings = overrides_from_environment(environ, {"SESSION_COOKIE_SECURE": False})
        self.assertEqual(settings["SESSION_COOKIE_AGE"], 3600)
        self.assertEqual(settings["MY_PACKAGE_SAMPLE_RATE"], 0.25)
        self.assertIs(settings["SESSION_COOKIE_SECURE"], True)
        self.assertEqual(settings["TIME_ZONE"], "America/Vancouver")
        self.assertEqual(settings["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(settings["SILENCED_SYSTEM_CHECKS"], ["security.W001", "security.W003"])
        self.assertEqual(settings["MESSAGE_TAGS"], {40: "danger"})
        none_setting = overrides_from_environment({"DJANGO_SECURE_PROXY_SSL_HEADER": "None"}, {})
        self.assertIsNone(none_setting["SECURE_PROXY_SSL_HEADER"])

    def test_a_bad_variable_names_itself(self):
        with self.assertRaisesRegex(SmarterOverridesError, "DJANGO_SESSION_COOKIE_AGE"):
            overrides_from_environment({"DJANGO_SESSION_COOKIE_AGE": "an hour"}, {"SESSION_COOKIE_AGE": 1})
        with self.assertRaisesRegex(SmarterOverridesError, "is not a Django setting name"):
            overrides_from_environment({"DJANGO_9LIVES": "1"}, {})


class TestApplyOverrides(SmarterTestBase):
    """The file, then the variables, supersede a settings module's namespace."""

    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "settings.yaml"

    def apply(self, file_text: str, environ: dict[str, str], settings: dict[str, object]) -> list[str]:
        self.path.write_text(file_text, encoding="utf-8")
        variables = {"SMARTER_OVERRIDES_FILE": str(self.path), **environ}
        return apply_overrides(settings, variables)

    def test_the_order(self):
        """Smarter's value, then the file's, then the variable's."""
        settings: dict[str, object] = {"SESSION_COOKIE_AGE": 1, "APPEND_SLASH": True, "LOGGING": {"version": 1}}
        file_text = "SESSION_COOKIE_AGE: 2\nLOGGING:\n  disable_existing_loggers: true\n"
        applied = self.apply(file_text, {"DJANGO_SESSION_COOKIE_AGE": "3"}, settings)
        self.assertEqual(applied, ["LOGGING", "SESSION_COOKIE_AGE"])
        self.assertEqual(settings["SESSION_COOKIE_AGE"], 3)
        self.assertIs(settings["APPEND_SLASH"], True)
        # a dictionary replaces Smarter's: it isn't merged.
        self.assertEqual(settings["LOGGING"], {"disable_existing_loggers": True})

    def test_redbeat_follows_the_broker(self):
        """RedBeat's Redis is computed from the broker's, so it moves with DJANGO_CELERY_BROKER_URL."""
        default = "redis://smarter-redis:6379/0"
        broker = "redis://:pw@redis.example.test:6379/0"
        settings: dict[str, object] = {"CELERY_BROKER_URL": default, "CELERY_REDBEAT_REDIS_URL": default}
        applied = self.apply("", {"DJANGO_CELERY_BROKER_URL": broker}, settings)
        self.assertEqual(applied, ["CELERY_BROKER_URL", "CELERY_REDBEAT_REDIS_URL"])
        self.assertEqual(settings["CELERY_REDBEAT_REDIS_URL"], broker)

    def test_redbeat_of_its_own_stays(self):
        """A RedBeat url that an override, or a settings module, set apart from the broker's is not replaced."""
        default = "redis://smarter-redis:6379/0"
        broker = "redis://:pw@redis.example.test:6379/0"
        redbeat = "redis://:pw@redbeat.example.test:6379/3"
        cases: tuple[tuple[dict[str, str], dict[str, object]], ...] = (
            (
                {"DJANGO_CELERY_BROKER_URL": broker, "DJANGO_CELERY_REDBEAT_REDIS_URL": redbeat},
                {"CELERY_BROKER_URL": default, "CELERY_REDBEAT_REDIS_URL": default},
            ),
            ({"DJANGO_CELERY_BROKER_URL": broker}, {"CELERY_BROKER_URL": default, "CELERY_REDBEAT_REDIS_URL": redbeat}),
        )
        for environ, settings in cases:
            with self.subTest(environ=environ):
                self.apply("", environ, settings)
                self.assertEqual(settings["CELERY_REDBEAT_REDIS_URL"], redbeat)
        untouched: dict[str, object] = {"CELERY_BROKER_URL": default, "CELERY_REDBEAT_REDIS_URL": default}
        self.apply("", {"DJANGO_APPEND_SLASH": "false"}, untouched)
        self.assertEqual(untouched["CELERY_REDBEAT_REDIS_URL"], default)

    def test_the_file_gives_a_variable_its_type(self):
        settings: dict[str, object] = {}
        self.apply("SMARTER_TEST_LIMIT: 10\n", {"DJANGO_SMARTER_TEST_LIMIT": "20"}, settings)
        self.assertEqual(settings["SMARTER_TEST_LIMIT"], 20)

    def test_nothing_to_apply(self):
        settings: dict[str, object] = {"APPEND_SLASH": True}
        with patch(f"{MODULE}.logger") as logger:
            applied = apply_overrides(settings, {"SMARTER_OVERRIDES_FILE": str(self.path)})
        self.assertEqual(applied, [])
        self.assertEqual(settings, {"APPEND_SLASH": True})
        logger.info.assert_not_called()
        logger.warning.assert_not_called()

    def test_os_environ_by_default(self):
        settings: dict[str, object] = {"APPEND_SLASH": True}
        environ = {"SMARTER_OVERRIDES_FILE": str(self.path), "DJANGO_APPEND_SLASH": "false"}
        with patch.dict("os.environ", environ):
            apply_overrides(settings)
        self.assertIs(settings["APPEND_SLASH"], False)

    def test_an_unknown_setting_is_set_with_a_warning(self):
        """A setting that neither Django nor Smarter defines may be a package's, or a typo."""
        settings: dict[str, object] = {}
        with patch(f"{MODULE}.logger") as logger:
            self.apply("SESION_COOKIE_AGE: 1\n", {"DJANGO_TIME_ZONE": "UTC"}, settings)
        self.assertEqual(settings["SESION_COOKIE_AGE"], 1)
        self.assertEqual(settings["TIME_ZONE"], "UTC")
        logger.warning.assert_called_once()
        self.assertEqual(logger.warning.call_args.args[1], "SESION_COOKIE_AGE")

    def test_values_are_never_logged(self):
        """A setting may hold a password: the log names it, and never shows its value."""
        secret = f"unit-test-secret-{self.hash_suffix}"
        settings: dict[str, object] = {"EMAIL_HOST_PASSWORD": ""}
        file_text = f"DATABASES:\n  default:\n    PASSWORD: {secret}-file\n"
        environ = {"DJANGO_EMAIL_HOST_PASSWORD": f"{secret}-variable", "DJANGO_SMARTER_TEST_TOKEN": secret}
        with patch(f"{MODULE}.logger") as logger:
            self.apply(file_text, environ, settings)
        calls = logger.info.call_args_list + logger.warning.call_args_list
        logged = " ".join(str(argument) for call in calls for argument in call.args)
        self.assertIn("EMAIL_HOST_PASSWORD", logged)
        self.assertIn("DATABASES", logged)
        self.assertNotIn(secret, logged)
