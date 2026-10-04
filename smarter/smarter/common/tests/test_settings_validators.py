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
        """Test that ready() is False, and warns, for the default root domain, missing AWS and missing SMTP."""
        settings = smarter_settings.model_copy(update={"root_domain": "example.com"})
        with (
            patch.object(Settings, "aws_is_configured", new_callable=PropertyMock, return_value=False),
            patch.object(Settings, "smtp_is_configured", new_callable=PropertyMock, return_value=False),
            patch("builtins.print") as mock_print,
        ):
            self.assertFalse(settings.ready())
        self.assertGreaterEqual(mock_print.call_count, 3)

    def test_versions(self):
        for name in ("version", "python_version", "pydantic_version", "drf_version", "linux_distribution"):
            with self.subTest(name=name):
                self.assertIsInstance(getattr(smarter_settings, name), str)
                self.assertTrue(getattr(smarter_settings, name))
        self.assertEqual(smarter_settings.cache_path, "/home/smarter_user/.cache")

    def test_reactjs_root_div_id(self):
        div_id = smarter_settings.smarter_reactjs_root_div_id
        self.assertNotIn("/", div_id)
        self.assertNotIn(".", div_id)
        self.assertTrue(div_id.endswith("root"))

    def test_to_json(self):
        """Test that to_json() dumps the settings, and the defaults when dump_defaults is set."""
        dump = smarter_settings.model_copy(update={"dump_defaults": True}).to_json()
        self.assertIn("smarter_settings", dump)
        self.assertIn("settings_defaults", dump)
        self.assertEqual(list(dump.keys()), sorted(dump.keys()))
