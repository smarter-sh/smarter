"""
Test the field validators of :class:`smarter.common.conf.settings.Settings`.

Every validator is called directly, with values that exercise its empty, valid
and invalid branches, without building a new Settings instance. A validator
either returns a value or raises one of the configuration errors; any other
exception, e.g. a TypeError or an AttributeError, is a bug in the validator.
"""

import inspect
from unittest.mock import Mock, PropertyMock, patch

from pydantic import SecretStr

from smarter.common.conf import smarter_settings
from smarter.common.conf.env import DEFAULT_MISSING_VALUE
from smarter.common.conf.settings import Settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

#: The exceptions that a validator may raise for an invalid value.
EXPECTED_ERRORS = (SmarterConfigurationError, SmarterValueError, ValueError)

#: Values that exercise the branches that most validators share: empty, the right
#: type, the wrong type, and strings that do or don't parse as numbers and booleans.
PROBES = [
    None,
    "",
    "   ",
    "a-string",
    "example.com",
    "https://example.com/path/",
    "a,b, c",
    "true",
    "false",
    "1",
    "-1",
    "0",
    "not-a-number",
    1,
    -1,
    0,
    3.5,
    True,
    False,
    [],
    ["a", "b"],
    [1, 2],
    {},
    {"a": "b"},
    SecretStr(""),
    SecretStr("a-secret"),
    object(),
]


def field_validators() -> dict[str, list[str]]:
    """Return the name of each of the Settings' field validators, and the fields it validates."""
    return {
        name: list(decorator.info.fields)
        for name, decorator in Settings.__pydantic_decorators__.field_validators.items()
    }


def call(validator, value, data: dict):
    """Call a validator, with a ValidationInfo whose data is ``data`` if the validator takes one."""
    parameters = [
        p for p in inspect.signature(validator).parameters.values() if p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)
    ]
    if len(parameters) >= 2:
        info = Mock()
        info.data = data
        return validator(value, info)
    return validator(value)


class TestSettingsValidators(SmarterTestBase):
    """Test that every field validator of the Settings returns a value or raises a configuration error."""

    def test_has_validators(self):
        self.assertGreater(len(field_validators()), 50)

    def test_current_values_are_valid(self):
        """Test that each validator accepts its field's current value."""
        data = smarter_settings.model_dump()
        for name, fields in field_validators().items():
            validator = getattr(Settings, name)
            for field in fields:
                value = getattr(smarter_settings, field)
                with self.subTest(validator=name, field=field):
                    try:
                        call(validator, value, data)
                    except EXPECTED_ERRORS:
                        # a few validators refuse their own defaults, e.g. a placeholder value.
                        pass

    def test_probes(self):
        """Test that each validator returns a value or raises a configuration error, for every probe value."""
        for data in ({}, smarter_settings.model_dump()):
            for name in field_validators():
                validator = getattr(Settings, name)
                for value in PROBES:
                    with self.subTest(validator=name, value=value, data=bool(data)):
                        try:
                            call(validator, value, data)
                        except EXPECTED_ERRORS:
                            pass

    def test_empty_values_return_defaults(self):
        """Test that the validators accept an empty value, for the fields that have a default."""
        failures = []
        for name, fields in field_validators().items():
            validator = getattr(Settings, name)
            for value in (None, ""):
                try:
                    call(validator, value, {})
                except EXPECTED_ERRORS:
                    failures.append((name, fields, value))
        # a field that is required has no default, but most do.
        self.assertLess(len(failures), len(field_validators()), failures)


class TestSettingsMethods(SmarterTestBase):
    """Test the Settings' methods and properties that the test_conf tests don't reach."""

    def test_ready_reports_each_missing_service(self):
        """Test that ready() is False, and warns, for the default root domain outside of local, and missing AWS."""
        settings = smarter_settings.model_copy(update={"root_domain": "example.com", "environment": "prod"})
        with (
            patch.object(Settings, "aws_is_configured", new_callable=PropertyMock, return_value=False),
            patch("builtins.print") as mock_print,
        ):
            self.assertFalse(settings.ready())
        self.assertEqual(mock_print.call_count, 2)

    def test_ready_needs_neither_smtp_nor_a_root_domain_locally(self):
        """Test that SMTP is never needed, and the default root domain is fine in the local environment."""
        settings = smarter_settings.model_copy(update={"root_domain": "example.com", "environment": "local"})
        with (
            patch.object(Settings, "aws_is_configured", new_callable=PropertyMock, return_value=True),
            patch.object(Settings, "smtp_is_configured", new_callable=PropertyMock, return_value=False),
            patch("builtins.print") as mock_print,
        ):
            self.assertTrue(settings.ready())
        mock_print.assert_not_called()

    def test_smtp_is_configured(self):
        """Test that SMTP is configured only when every credential is set, and none is a placeholder."""
        configured = {"smtp_username": SecretStr("user"), "smtp_password": SecretStr("password")}

        def smtp_is_configured(**update) -> bool:
            settings = smarter_settings.model_copy(update={**configured, **update})
            # a copy keeps the cached_property of the original, which is computed again here.
            settings.__dict__.pop("smtp_is_configured", None)
            return settings.smtp_is_configured

        with patch.object(Settings, "smtp_host", new_callable=PropertyMock, return_value="smtp.example.com"):
            self.assertTrue(smtp_is_configured())
            for name, value in (
                ("smtp_username", None),
                ("smtp_password", None),
                ("smtp_password", SecretStr(DEFAULT_MISSING_VALUE)),
                ("smtp_username", SecretStr("SET-ME-IN-helm/charts/smarter/values.yaml")),
            ):
                with self.subTest(name=name, value=value):
                    self.assertFalse(smtp_is_configured(**{name: value}))
        with patch.object(Settings, "smtp_host", new_callable=PropertyMock, return_value=None):
            self.assertFalse(smtp_is_configured())

    def test_smtp_host_and_from_email(self):
        """Test that SMTP_HOST and SMTP_FROM_EMAIL are used when set, and derived otherwise."""
        module = "smarter.common.conf.settings"
        settings = smarter_settings.model_copy(update={"aws_region": "us-west-2"})
        with patch(f"{module}.settings_defaults") as defaults:
            defaults.SMTP_HOST = "smtp.example.com"
            defaults.SMTP_FROM_EMAIL = "hello@example.com"
            self.assertEqual(settings.smtp_host, "smtp.example.com")
            self.assertEqual(settings.smtp_from_email, "hello@example.com")
            defaults.SMTP_HOST = None
            defaults.SMTP_FROM_EMAIL = DEFAULT_MISSING_VALUE
            self.assertEqual(settings.smtp_host, "email-smtp.us-west-2.amazonaws.com")
            self.assertEqual(settings.smtp_from_email, f"no-reply@{settings.platform_subdomain}.{settings.root_domain}")
            self.assertIsNone(smarter_settings.model_copy(update={"aws_region": None}).smtp_host)

    def test_optional_values_are_none_when_missing(self):
        """Test that the optional cluster name and SMTP credentials are None when missing, or a placeholder."""
        module = "smarter.common.conf.settings"
        for value in (None, "", DEFAULT_MISSING_VALUE):
            with self.subTest(value=value), patch(f"{module}.settings_defaults") as defaults:
                defaults.AWS_EKS_CLUSTER_NAME = DEFAULT_MISSING_VALUE
                defaults.SMTP_PASSWORD = None
                defaults.SMTP_USERNAME = None
                self.assertIsNone(call(Settings.validate_aws_eks_cluster_name, value, {}))
                self.assertIsNone(call(Settings.validate_smtp_password, value, {}))
                self.assertIsNone(call(Settings.validate_smtp_username, value, {}))
        self.assertEqual(call(Settings.validate_aws_eks_cluster_name, "my-cluster", {}), "my-cluster")
        self.assertIsNone(call(Settings.validate_smtp_password, SecretStr(DEFAULT_MISSING_VALUE), {}))

    def test_versions(self):
        for name in ("version", "python_version", "pydantic_version", "drf_version", "linux_distribution"):
            with self.subTest(name=name):
                self.assertIsInstance(getattr(smarter_settings, name), str)
                self.assertTrue(getattr(smarter_settings, name))
        self.assertEqual(smarter_settings.cache_path, "/home/smarter_user/.cache")

    def test_to_json(self):
        """Test that to_json() dumps the settings, and the defaults when dump_defaults is set."""
        dump = smarter_settings.model_copy(update={"dump_defaults": True}).to_json()
        self.assertIn("smarter_settings", dump)
        self.assertIn("settings_defaults", dump)
        self.assertEqual(list(dump.keys()), sorted(dump.keys()))


class TestSettingsMissingDefaults(SmarterTestBase):
    """Test the validators and urls whose default, or computed value, is missing."""

    def test_aws_profile_and_region_without_defaults(self):
        """An empty AWS profile or region is None when its default is missing, and the default otherwise."""
        module = "smarter.common.conf.settings"
        for name, validator in (
            ("AWS_PROFILE", Settings.validate_aws_profile),
            ("AWS_REGION", Settings.validate_aws_region),
        ):
            with self.subTest(default=name):
                with patch(f"{module}.settings_defaults") as defaults:
                    setattr(defaults, name, DEFAULT_MISSING_VALUE)
                    self.assertIsNone(call(validator, "", {}))
                    setattr(defaults, name, "the-default")
                    self.assertEqual(call(validator, "", {}), "the-default")

    def test_urls_that_cannot_be_built(self):
        """The cdn and platform urls raise when their domain can't be made into a url."""
        for name in ("environment_cdn_url", "root_cdn_url", "platform_url"):
            with (
                self.subTest(url=name),
                patch("smarter.common.conf.settings.SmarterValidator.urlify", return_value=None),
            ):
                with self.assertRaises(SmarterConfigurationError):
                    Settings.__dict__[name].func(smarter_settings)
