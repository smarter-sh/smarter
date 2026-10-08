"""Test :func:`smarter.common.conf.env.get_env`."""

import os
from unittest import TestCase
from unittest.mock import patch

from pydantic import SecretStr

from smarter.common.conf import env
from smarter.common.conf.env import DEFAULT_MISSING_VALUE, get_env, is_missing_value

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
        self.assertIsNone(self.get(DEFAULT_MISSING_VALUE, "default"))

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
