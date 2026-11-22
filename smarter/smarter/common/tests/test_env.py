"""Test :func:`smarter.common.conf.env.get_env`, and the helpers it and the settings source share."""

import os
from unittest import TestCase
from unittest.mock import patch

from pydantic import SecretStr

from smarter.common.conf import env
from smarter.common.conf.const import DEFAULT_MISSING_VALUE
from smarter.common.conf.env import (
    cast_environment_value,
    get_env,
    is_missing_value,
    read_environment_variable,
    unquoted,
)

VAR = "TEST_SMARTER_GET_ENV"


class TestGetEnv(TestCase):
    """Test that get_env() reads, and casts, an environment variable to the type of its default."""

    def get(self, value, default, **kwargs):
        with patch.dict(os.environ, {VAR: value}):
            return get_env(VAR, default, **kwargs)

    def test_missing(self):
        """Test that a missing variable is its default, also when it is required."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(VAR, None)
            os.environ.pop(f"SMARTER_{VAR}", None)
            self.assertEqual(get_env(VAR, "default"), "default")
            self.assertEqual(get_env(VAR, "default", is_required=True), "default")

    def test_smarter_prefix(self):
        with patch.dict(os.environ, {f"SMARTER_{VAR}": "prefixed"}):
            os.environ.pop(VAR, None)
            self.assertEqual(get_env(VAR, ""), "prefixed")

    def test_missing_value_marker(self):
        """Test that a variable holding the placeholder is its default, of the default's type."""
        self.assertEqual(self.get(DEFAULT_MISSING_VALUE, "default"), "default")
        self.assertEqual(self.get(DEFAULT_MISSING_VALUE, 587), 587)
        self.assertFalse(self.get(DEFAULT_MISSING_VALUE, False))
        self.assertEqual(self.get(DEFAULT_MISSING_VALUE, ["a"]), ["a"])
        self.assertIsNone(self.get(DEFAULT_MISSING_VALUE, None))

    def test_str(self):
        self.assertEqual(self.get(' "quoted value" ', ""), "quoted value")

    def test_bool(self):
        self.assertTrue(self.get("yes", False))
        self.assertFalse(self.get("no", True))

    def test_int(self):
        self.assertEqual(self.get("42", 0), 42)
        self.assertEqual(self.get("not an int", 7), 7)

    def test_float(self):
        self.assertEqual(self.get("1.5", 0.0), 1.5)
        self.assertEqual(self.get("not a float", 2.5), 2.5)

    def test_list(self):
        self.assertEqual(self.get("a, b,,c", []), ["a", "b", "c"])

    def test_dict(self):
        self.assertEqual(self.get('{"a": 1}', {}), {"a": 1})
        self.assertEqual(self.get("not json", {"b": 2}), {"b": 2})

    def test_other_type(self):
        self.assertEqual(self.get("value", None), "value")

    def test_verbose_secret(self):
        """Test that a secret is masked in the verbose console output."""
        with patch.object(env, "VERBOSE_CONSOLE_OUTPUT", True), patch("builtins.print") as mock_print:
            self.assertEqual(self.get("secret-value", "", is_secret=True), "secret-value")
        self.assertIn("****", mock_print.call_args.args[0])
        self.assertNotIn("secret-value", mock_print.call_args.args[0])


class TestIsMissingValue(TestCase):
    """Test that is_missing_value() recognizes unset values and placeholders."""

    def test_missing(self):
        for value in (
            None,
            "",
            "  ",
            DEFAULT_MISSING_VALUE,
            "set-me-please",
            "SET-ME-IN-helm/charts/smarter/values.yaml",
        ):
            with self.subTest(value=value):
                self.assertTrue(is_missing_value(value))
                self.assertTrue(is_missing_value(SecretStr(value) if value is not None else None))

    def test_set(self):
        for value in ("sk-key", "example.com", 0, 587, False):
            with self.subTest(value=value):
                self.assertFalse(is_missing_value(value))
        self.assertFalse(is_missing_value(SecretStr("sk-key")))


class TestReadEnvironmentVariable(TestCase):
    """Test that read_environment_variable() reads a variable with or without SMARTER_, and strips it."""

    def setUp(self):
        for name in (VAR, f"SMARTER_{VAR}"):
            patcher = patch.dict(os.environ, {}, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)
            os.environ.pop(name, None)

    def test_missing(self):
        self.assertIsNone(read_environment_variable(VAR))

    def test_unprefixed_wins(self):
        with patch.dict(os.environ, {VAR: "plain", f"SMARTER_{VAR}": "prefixed"}):
            self.assertEqual(read_environment_variable(VAR), "plain")

    def test_prefixed(self):
        """The prefixed name is read when the plain one is missing, or empty."""
        with patch.dict(os.environ, {f"SMARTER_{VAR}": "prefixed"}):
            self.assertEqual(read_environment_variable(VAR), "prefixed")
        with patch.dict(os.environ, {VAR: "", f"SMARTER_{VAR}": "prefixed"}):
            self.assertEqual(read_environment_variable(VAR), "prefixed")

    def test_strips_whitespace_and_quotes(self):
        with patch.dict(os.environ, {VAR: '  "quoted"  '}):
            self.assertEqual(read_environment_variable(VAR), "quoted")


class TestUnquoted(TestCase):
    """Test that unquoted() strips whitespace and one pair of matching quotes, and nothing else."""

    def test_matching_quotes(self):
        self.assertEqual(unquoted('"https://example.com/contact/"'), "https://example.com/contact/")
        self.assertEqual(unquoted("'single'"), "single")
        self.assertEqual(unquoted('  " padded "  '), "padded")

    def test_unquoted_and_unmatched(self):
        """A value without a matching pair keeps its quotes, and inner quotes are kept."""
        self.assertEqual(unquoted("plain"), "plain")
        self.assertEqual(unquoted('"unmatched'), '"unmatched')
        self.assertEqual(unquoted("\"mixed'"), "\"mixed'")
        self.assertEqual(unquoted('say "hi"'), 'say "hi"')
        self.assertEqual(unquoted('"'), '"')
        self.assertEqual(unquoted('""'), "")


class TestCastEnvironmentValue(TestCase):
    """Test that cast_environment_value() casts to the default's type, and never logs the value."""

    def test_casts(self):
        self.assertEqual(cast_environment_value(VAR, " text ", "default"), "text")
        self.assertIs(cast_environment_value(VAR, "yes", False), True)
        self.assertEqual(cast_environment_value(VAR, "7", 0), 7)
        self.assertEqual(cast_environment_value(VAR, "1.5", 0.0), 1.5)
        self.assertEqual(cast_environment_value(VAR, "a, b,", []), ["a", "b"])
        self.assertEqual(cast_environment_value(VAR, '{"a": 1}', {}), {"a": 1})
        self.assertEqual(cast_environment_value(VAR, "raw", None), "raw")

    def test_missing_is_the_default(self):
        self.assertEqual(cast_environment_value(VAR, None, 3), 3)
        self.assertEqual(cast_environment_value(VAR, DEFAULT_MISSING_VALUE, 3), 3)

    def test_uncastable_is_the_default_and_the_value_is_not_logged(self):
        for raw, default in (("secret-value", 0), ("secret-value", 0.0), ("secret-value", {})):
            with self.subTest(default=default):
                with self.assertLogs("smarter.common.conf.env", level="WARNING") as captured:
                    self.assertEqual(cast_environment_value(VAR, raw, default), default)
                message = captured.records[0].getMessage()
                self.assertIn(VAR, message)
                self.assertNotIn("secret-value", message)
