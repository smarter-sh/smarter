"""
Test the field validators of :class:`smarter.common.conf.settings.Settings`.

Every validator is called directly, with values that exercise its empty, valid
and invalid branches, without building a new Settings instance. A validator
either returns a value or raises one of the configuration errors; any other
exception, e.g. a TypeError or an AttributeError, is a bug in the validator.
"""

import inspect
from contextlib import contextmanager
from typing import Iterator, Optional
from unittest.mock import Mock, PropertyMock, patch

from botocore.exceptions import (
    EndpointConnectionError,
    NoCredentialsError,
    ProfileNotFound,
)
from pydantic import SecretStr

from smarter.common.conf import smarter_settings
from smarter.common.conf.const import DEFAULT_MISSING_VALUE
from smarter.common.conf.settings import Settings
from smarter.common.conf.settings.aws import AWS_REGIONS, aws_credentials_work
from smarter.common.conf.util import field_default
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib.typing import SmarterDictType
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
    """
    Return the name of each of the Settings' field validators, and the fields it validates.

    A wildcard validator, ``@field_validator("*")``, validates every field: its ``*`` is expanded to
    the names of all the fields, so that it is called with a real field's name.
    """
    every_field = list(Settings.model_fields)
    return {
        name: [field for pattern in decorator.info.fields for field in (every_field if pattern == "*" else [pattern])]
        for name, decorator in Settings.__pydantic_decorators__.field_validators.items()
    }


@contextmanager
def patched_defaults(module: str) -> Iterator[dict[str, object]]:
    """
    Replace some fields' defaults, as the validators of one settings module see them.

    :param module: The settings module, e.g. ``smarter.common.conf.settings.email``.
    :returns: A dict to put the replacements in, by field name. The other fields keep their defaults.
    """
    replacements: dict[str, object] = {}

    def fake_field_default(model, field_name: str) -> object:
        if field_name in replacements:
            return replacements[field_name]
        return field_default(model, field_name)

    with patch(f"{module}.field_default", side_effect=fake_field_default):
        yield replacements


def call(validator, value, data: SmarterDictType, field_name: Optional[str] = None):
    """Call a validator, with a ValidationInfo whose data is ``data`` if the validator takes one."""
    parameters = [
        p for p in inspect.signature(validator).parameters.values() if p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)
    ]
    if len(parameters) >= 2:
        info = Mock()
        info.data = data
        info.field_name = field_name
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
                        call(validator, value, data, field)
                    except EXPECTED_ERRORS:
                        # a few validators refuse their own defaults, e.g. a placeholder value.
                        pass

    def test_probes(self):
        """Test that each validator returns a value or raises a configuration error, for every probe value."""
        for data in ({}, smarter_settings.model_dump()):
            for name, fields in field_validators().items():
                validator = getattr(Settings, name)
                for value in PROBES:
                    with self.subTest(validator=name, value=value, data=bool(data)):
                        try:
                            call(validator, value, data, fields[0])
                        except EXPECTED_ERRORS:
                            pass

    def test_empty_values_return_defaults(self):
        """Test that the validators accept an empty value, for the fields that have a default."""
        failures = []
        for name, fields in field_validators().items():
            validator = getattr(Settings, name)
            for value in (None, ""):
                try:
                    call(validator, value, {}, fields[0])
                except EXPECTED_ERRORS:
                    failures.append((name, fields, value))
        # a field that is required has no default, but most do.
        self.assertLess(len(failures), len(field_validators()), failures)

    def test_database_read_timeout(self):
        """Test that the database read timeout parses seconds, defaults to no timeout, and rejects text."""
        validator = Settings.parse_database_read_timeout
        self.assertEqual(call(validator, "60", {}), 60)
        self.assertEqual(call(validator, 30, {}), 30)
        self.assertEqual(call(validator, "", {}), 0)
        with self.assertRaises(SmarterConfigurationError):
            call(validator, "a minute", {})

    def test_prompt_threads(self):
        """Test that the prompt threads parse a count, default to 32, and reject text."""
        validator = Settings.parse_prompt_threads
        self.assertEqual(call(validator, "8", {}), 8)
        self.assertEqual(call(validator, 16, {}), 16)
        self.assertEqual(call(validator, "", {}), 32)
        with self.assertRaises(SmarterConfigurationError):
            call(validator, "many", {})

    def test_prompt_history_max_age(self):
        """Test that the prompt history's max age parses days, defaults to 90, and rejects text and zero."""
        validator = Settings.parse_prompt_history_max_age
        self.assertEqual(call(validator, "30", {}), 30)
        self.assertEqual(call(validator, 365, {}), 365)
        self.assertEqual(call(validator, "", {}), 90)
        self.assertEqual(call(validator, None, {}), 90)
        for value in ("forever", "0", "-1"):
            with self.subTest(value=value), self.assertRaises(SmarterConfigurationError):
                call(validator, value, {})

    def test_sql_port(self):
        """Test that the database port parses an environment variable's string, defaults, and rejects non-ports."""
        validator = Settings.validate_subsystem_sql_port
        self.assertEqual(call(validator, "3307", {}), 3307)
        self.assertEqual(call(validator, 3306, {}), 3306)
        self.assertEqual(call(validator, "", {}), 3306)
        self.assertEqual(call(validator, DEFAULT_MISSING_VALUE, {}), 3306)
        for value in ("not-a-port", "0", "65536", "-1"):
            with self.subTest(port=value), self.assertRaises(SmarterConfigurationError):
                call(validator, value, {})

    def test_mysql_names(self):
        """Test that the database host, name and user are trimmed, default when missing, and reject non-strings."""
        for validator, default in (
            (Settings.validate_subsystem_sql_host, "smarter-mariadb"),
            (Settings.validate_subsystem_sql_database, "smarter"),
            (Settings.validate_subsystem_sql_user, "smarter"),
        ):
            with self.subTest(validator=validator.__name__):
                self.assertEqual(call(validator, " db.example.com ", {}), "db.example.com")
                self.assertEqual(call(validator, "", {}), default)
                self.assertEqual(call(validator, DEFAULT_MISSING_VALUE, {}), default)
                with self.assertRaises(SmarterConfigurationError):
                    call(validator, 42, {})

    def test_sql_password(self):
        """Test that the database password is a SecretStr, and that a placeholder is no password."""
        validator = Settings.validate_subsystem_sql_password
        self.assertEqual(call(validator, "s3cret", {}).get_secret_value(), "s3cret")
        self.assertEqual(call(validator, SecretStr("s3cret"), {}).get_secret_value(), "s3cret")
        self.assertIsNone(call(validator, DEFAULT_MISSING_VALUE, {}))
        self.assertIsNone(call(validator, "SET-ME-IN-helm/charts/smarter/values.yaml", {}))
        with self.assertRaises(SmarterConfigurationError):
            call(validator, 42, {})

    def test_databases_come_from_smarter_settings(self):
        """Test that Django's DATABASES is built from smarter_settings, not read from the environment."""
        # pylint: disable=import-outside-toplevel
        from django.conf import settings

        database = settings.DATABASES["default"]
        self.assertEqual(database["HOST"], smarter_settings.subsystem_sql_host)
        self.assertEqual(database["PORT"], str(smarter_settings.subsystem_sql_port))
        self.assertEqual(database["USER"], smarter_settings.subsystem_sql_user)
        self.assertIsNotNone(smarter_settings.subsystem_sql_password, "the local environment has a default password")


class TestSettingsMethods(SmarterTestBase):
    """Test the Settings' methods and properties that the test_conf tests don't reach."""

    def test_ready_reports_each_missing_service(self):
        """Test that ready() is False, and warns, for the default root domain outside of local, and missing AWS."""
        settings = smarter_settings.model_copy(update={"platform_root_domain": "example.com", "environment": "prod"})
        with (
            patch.object(Settings, "aws_is_configured", new_callable=PropertyMock, return_value=False),
            patch("builtins.print") as mock_print,
        ):
            self.assertFalse(settings.ready())
        self.assertEqual(mock_print.call_count, 2)

    def test_ready_needs_neither_smtp_nor_a_root_domain_locally(self):
        """Test that SMTP is never needed, and the default root domain is fine in the local environment."""
        settings = smarter_settings.model_copy(update={"platform_root_domain": "example.com", "environment": "local"})
        with (
            patch.object(Settings, "aws_is_configured", new_callable=PropertyMock, return_value=True),
            patch.object(Settings, "smtp_is_configured", new_callable=PropertyMock, return_value=False),
            patch("builtins.print") as mock_print,
        ):
            self.assertTrue(settings.ready())
        mock_print.assert_not_called()

    def test_smtp_is_configured(self):
        """Test that SMTP is configured only when every credential is set, and none is a placeholder."""
        configured = {
            "subsystem_smtp_host": "smtp.example.com",
            "subsystem_smtp_username": SecretStr("user"),
            "subsystem_smtp_password": SecretStr("password"),
        }

        def smtp_is_configured(**update) -> bool:
            settings = smarter_settings.model_copy(update={**configured, **update})
            # a copy keeps the cached_property of the original, which is computed again here.
            settings.__dict__.pop("smtp_is_configured", None)
            return settings.smtp_is_configured

        self.assertTrue(smtp_is_configured())
        for name, value in (
            ("subsystem_smtp_username", None),
            ("subsystem_smtp_password", None),
            ("subsystem_smtp_password", SecretStr(DEFAULT_MISSING_VALUE)),
            ("subsystem_smtp_username", SecretStr("SET-ME-IN-helm/charts/smarter/values.yaml")),
            ("subsystem_smtp_host", None),
        ):
            with self.subTest(name=name, value=value):
                self.assertFalse(smtp_is_configured(**{name: value}))

    def test_smtp_host_and_from_email(self):
        """Test that SMTP_HOST and SMTP_FROM_EMAIL are used when set, and derived otherwise."""
        configured = smarter_settings.model_copy(
            update={
                "subsystem_smtp_host": "smtp.example.com",
                "subsystem_smtp_from_email": "hello@example.com",
            }
        )
        self.assertEqual(configured.subsystem_smtp_host, "smtp.example.com")
        self.assertEqual(configured.subsystem_smtp_from_email, "hello@example.com")
        derived = Settings(aws_region="us-west-2", subsystem_smtp_host=None, subsystem_smtp_from_email="")
        self.assertEqual(derived.subsystem_smtp_host, "email-smtp.us-west-2.amazonaws.com")
        self.assertEqual(
            derived.subsystem_smtp_from_email,
            f"no-reply@{derived.platform_subdomain}.{derived.platform_root_domain}",
        )
        no_region = Settings(aws_region="", subsystem_smtp_host=None)
        self.assertIsNone(no_region.subsystem_smtp_host)

    def test_admin_credentials(self):
        """Test that the admin username falls back to its default, and the password is None when missing, or a placeholder."""
        module = "smarter.common.conf.settings.security"
        with patched_defaults(module) as defaults:
            for value in (None, ""):
                with self.subTest(value=value):
                    self.assertEqual(call(Settings.validate_platform_admin_username, value, {}), "admin")
                    self.assertIsNone(call(Settings.validate_platform_admin_password, value, {}))
            self.assertEqual(call(Settings.validate_platform_admin_username, "platform-admin", {}), "platform-admin")
            self.assertIsNone(call(Settings.validate_platform_admin_password, SecretStr(DEFAULT_MISSING_VALUE), {}))
            self.assertEqual(
                call(Settings.validate_platform_admin_password, SecretStr("pw"), {}).get_secret_value(), "pw"
            )
            with self.assertRaises(SmarterConfigurationError):
                call(Settings.validate_platform_admin_password, "not a SecretStr", {})
            defaults["platform_admin_username"] = ""
            with self.assertRaises(SmarterConfigurationError):
                call(Settings.validate_platform_admin_username, None, {})

    def test_optional_values_are_none_when_missing(self):
        """Test that the optional cluster name and SMTP credentials are None when missing, or a placeholder."""
        package = "smarter.common.conf.settings"
        for value in (None, "", DEFAULT_MISSING_VALUE):
            with (
                self.subTest(value=value),
                patched_defaults(f"{package}.aws") as aws_defaults,
            ):
                aws_defaults["subsystem_k8s_cluster_name"] = DEFAULT_MISSING_VALUE
                self.assertIsNone(call(Settings.validate_subsystem_k8s_cluster_name, value, {}))
                self.assertIsNone(call(Settings.validate_subsystem_smtp_password, value, {}))
                self.assertIsNone(call(Settings.validate_subsystem_smtp_username, value, {}))
        self.assertEqual(call(Settings.validate_subsystem_k8s_cluster_name, "my-cluster", {}), "my-cluster")
        self.assertIsNone(call(Settings.validate_subsystem_smtp_password, SecretStr(DEFAULT_MISSING_VALUE), {}))

    def test_github_token(self):
        """Test that the GitHub token is None when missing, or a placeholder, and must be a SecretStr."""
        placeholders = (None, "", DEFAULT_MISSING_VALUE, SecretStr("SET-ME-IN-helm/charts/smarter/values.yaml"))
        for value in placeholders:
            with self.subTest(value=value):
                self.assertIsNone(call(Settings.validate_github_token, value, {}))
        token = SecretStr("ghp_" + "x" * 36)
        self.assertIs(call(Settings.validate_github_token, token, {}), token)
        with self.assertRaises(SmarterConfigurationError):
            call(Settings.validate_github_token, "github-token", {})

    def test_account_manager_api_key(self):
        """Test that Account Manager's key is None when missing, or a placeholder, and must be a SecretStr."""
        for value in (None, "", DEFAULT_MISSING_VALUE, SecretStr("SET-ME-PLEASE")):
            with self.subTest(value=value):
                self.assertIsNone(call(Settings.validate_account_manager_api_key, value, {}))
        key = SecretStr("a-platform-key")
        self.assertIs(call(Settings.validate_account_manager_api_key, key, {}), key)
        with self.assertRaises(SmarterConfigurationError):
            call(Settings.validate_account_manager_api_key, "a-platform-key", {})

    def test_slack_bot_token(self):
        """Test that the Slack bot token is None when missing, or a placeholder, and must be a SecretStr."""
        for value in (None, "", DEFAULT_MISSING_VALUE, SecretStr("SET-ME-IN-helm/charts/smarter/values.yaml")):
            with self.subTest(value=value):
                self.assertIsNone(call(Settings.validate_subsystem_slack_bot_token, value, {}))
        token = SecretStr("xoxb-test")
        self.assertIs(call(Settings.validate_subsystem_slack_bot_token, token, {}), token)
        with self.assertRaises(SmarterConfigurationError):
            call(Settings.validate_subsystem_slack_bot_token, "xoxb-test", {})

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
        self.assertIn("defaults", dump)
        self.assertEqual(list(dump.keys()), sorted(dump.keys()))


class TestSettingsMissingDefaults(SmarterTestBase):
    """Test the validators and urls whose default, or computed value, is missing."""

    def test_aws_profile_and_region_without_defaults(self):
        """An empty AWS profile or region is None when its default is missing, and the default otherwise."""
        module = "smarter.common.conf.settings.aws"
        for name, validator in (
            ("aws_profile", Settings.validate_aws_profile),
            ("aws_region", Settings.validate_aws_region),
        ):
            with self.subTest(default=name):
                with patched_defaults(module) as defaults:
                    defaults[name] = DEFAULT_MISSING_VALUE
                    self.assertIsNone(call(validator, "", {}))
                    defaults[name] = "the-default"
                    self.assertEqual(call(validator, "", {}), "the-default")

    def test_urls_that_cannot_be_built(self):
        """The cdn and platform urls raise when their domain can't be made into a url."""
        for name in ("environment_cdn_url", "root_cdn_url", "platform_url"):
            with (
                self.subTest(url=name),
                patch("smarter.common.conf.settings.domains.SmarterValidator.urlify", return_value=None),
            ):
                with self.assertRaises(SmarterConfigurationError):
                    getattr(Settings, name).func(smarter_settings)


class TestStaticAwsKeyPairWarning(SmarterTestBase):
    """A real AWS key pair is logged as a security risk, once, by name only; an IAM role is preferred."""

    MODULE = "smarter.common.conf.settings.aws"
    ACCESS_KEY_ID = "AKIA" + "Z" * 16
    """Shaped like an access key id, which the validator checks, but not one."""
    SECRET_ACCESS_KEY = "z" * 40
    """Shaped like a secret access key, but not one."""

    def setUp(self):
        super().setUp()
        warned = patch(f"{self.MODULE}._warned_static_aws_key_pair", False)
        warned.start()
        self.addCleanup(warned.stop)

    def test_a_key_pair_is_a_warning_once(self):
        """Both keys validate, and the pair is reported once, naming the setting, never the value."""
        with self.assertLogs(self.MODULE, level="WARNING") as captured:
            self.assertIsNotNone(call(Settings.validate_aws_access_key_id, SecretStr(self.ACCESS_KEY_ID), {}))
            self.assertIsNotNone(call(Settings.validate_aws_secret_access_key, SecretStr(self.SECRET_ACCESS_KEY), {}))
        self.assertEqual(len(captured.records), 1)
        message = captured.records[0].getMessage()
        self.assertIn("SECURITY WARNING", message)
        self.assertIn("smarter_settings.aws_access_key_id", message)
        self.assertIn("IRSA", message)
        self.assertIn("smarter-infrastructure", message)
        self.assertIn("serviceAccount.awsRoleArn", message)
        self.assertNotIn(self.ACCESS_KEY_ID, message)
        self.assertNotIn(self.SECRET_ACCESS_KEY, message)

    def test_no_key_pair_is_no_warning(self):
        """No keys, a placeholder, or keys that an AWS profile overrides, log nothing."""
        with patch(f"{self.MODULE}.logger") as logger:
            for value in (None, SecretStr(""), SecretStr(DEFAULT_MISSING_VALUE)):
                with self.subTest(value=value):
                    self.assertIsNone(call(Settings.validate_aws_access_key_id, value, {}))
                    self.assertIsNone(call(Settings.validate_aws_secret_access_key, value, {}))
            profile = {"aws_profile": "smarter"}
            self.assertIsNone(call(Settings.validate_aws_access_key_id, SecretStr(self.ACCESS_KEY_ID), profile))
        # the profile case logs that the key is ignored; nothing logs the security warning.
        for logged in logger.warning.call_args_list:
            self.assertNotIn("SECURITY WARNING", str(logged.args[0]))


class TestAwsCredentialsWork(SmarterTestBase):
    """Aws_is_configured asks STS whether the credentials work, with a faked boto3 session: never AWS itself."""

    MODULE = "smarter.common.conf.settings.aws"

    def fake_session(self, credentials: Optional[object], sts_error: Optional[Exception] = None) -> Mock:
        """A boto3 session with these credentials, whose STS client raises sts_error, or answers."""
        session = Mock()
        session.get_credentials.return_value = credentials
        sts = session.client.return_value
        if sts_error is not None:
            sts.get_caller_identity.side_effect = sts_error
        return session

    def test_working_credentials(self):
        session = self.fake_session(credentials=object())
        with patch(f"{self.MODULE}.boto3.Session", return_value=session):
            self.assertTrue(aws_credentials_work())
        session.client.assert_called_once_with("sts")
        session.client.return_value.get_caller_identity.assert_called_once_with()

    def test_no_credentials(self):
        session = self.fake_session(credentials=None)
        with patch(f"{self.MODULE}.boto3.Session", return_value=session):
            with self.assertLogs(self.MODULE, level="WARNING"):
                self.assertFalse(aws_credentials_work())
        session.client.assert_not_called()

    def test_rejected_credentials(self):
        errors = [NoCredentialsError(), ProfileNotFound(profile="smarter"), EndpointConnectionError(endpoint_url="x")]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                session = self.fake_session(credentials=object(), sts_error=error)
                with patch(f"{self.MODULE}.boto3.Session", return_value=session):
                    with self.assertLogs(self.MODULE, level="WARNING"):
                        self.assertFalse(aws_credentials_work())

    def test_unexpected_error_logs_its_type_only(self):
        """An error's message can carry an account id or an ARN, so only its type is logged."""
        error = RuntimeError("arn:aws:iam::000000000000:user/someone is not authorized")
        session = self.fake_session(credentials=object(), sts_error=error)
        with patch(f"{self.MODULE}.boto3.Session", return_value=session):
            with self.assertLogs(self.MODULE, level="WARNING") as captured:
                self.assertFalse(aws_credentials_work())
        message = captured.records[0].getMessage()
        self.assertIn("RuntimeError", message)
        self.assertNotIn("arn:aws", message)

    def test_aws_is_configured_uses_it(self):
        """Settings() asks STS once, in ready(), and the property keeps its answer."""
        with patch(f"{self.MODULE}.aws_credentials_work", return_value=False) as works:
            settings = Settings()
            self.assertEqual(works.call_count, 1)
            self.assertFalse(settings.aws_is_configured)
            self.assertFalse(settings.aws_is_configured)
        self.assertEqual(works.call_count, 1)

    def test_the_tool_worker_never_asks(self):
        """The tool worker has no AWS credentials, by design (ADR-038): STS isn't asked, and nothing warns."""
        with (
            patch(f"{self.MODULE}.aws_credentials_work") as works,
            patch("builtins.print") as mock_print,
        ):
            settings = Settings(database_unavailable=True)
            self.assertFalse(settings.aws_is_configured)
        works.assert_not_called()
        for call in mock_print.call_args_list:
            self.assertNotIn("AWS is not configured", str(call))

    def test_aws_is_configured_asks_each_settings_once(self):
        """Each Settings instance asks for itself, so that a new one sees credentials that have changed."""
        with patch(f"{self.MODULE}.aws_credentials_work", side_effect=[False, True]) as works:
            first = Settings()
            second = Settings()
        self.assertFalse(first.aws_is_configured)
        self.assertTrue(second.aws_is_configured)
        self.assertEqual(works.call_count, 2)

    def test_aws_regions_default(self):
        """The default lists every commercial region, opt-in ones included, and validates aws_region against them."""
        self.assertIn("us-east-1", AWS_REGIONS)
        self.assertIn("af-south-1", AWS_REGIONS)
        self.assertEqual(len(AWS_REGIONS), len(set(AWS_REGIONS)))
        settings = Settings(aws_region="ap-southeast-4")
        self.assertEqual(settings.aws_region, "ap-southeast-4")
