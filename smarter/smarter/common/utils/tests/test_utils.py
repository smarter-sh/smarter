"""Test utility functions."""

import base64
import os

from smarter.common.exceptions import SmarterValueError
from smarter.common.utils.utils import (
    bool_environment_variable,
    generate_fernet_encryption_key,
    hash_factory,
    is_async_context,
    mask_string,
)
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getLogger(__name__)


class TestUtils(SmarterTestBase):
    """
    Test utility functions.
    """

    def test_hash_factory_default_length(self):
        token = hash_factory()
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 16)
        # Should be hex
        int(token, 16)

    def test_hash_factory_custom_length(self):
        token = hash_factory(32)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 32)
        int(token, 16)

    def test_is_async_context(self):
        # Should be False in normal sync test
        self.assertFalse(is_async_context())

    def test_bool_environment_variable_true(self):
        os.environ["TEST_BOOL"] = "true"
        self.assertTrue(bool_environment_variable("TEST_BOOL", False))
        os.environ["SMARTER_TEST_BOOL"] = "yes"
        del os.environ["TEST_BOOL"]
        self.assertTrue(bool_environment_variable("TEST_BOOL", False))
        del os.environ["SMARTER_TEST_BOOL"]

    def test_bool_environment_variable_false_and_default(self):
        os.environ["TEST_BOOL"] = "no"
        self.assertFalse(bool_environment_variable("TEST_BOOL", True))
        del os.environ["TEST_BOOL"]

        self.assertTrue(bool_environment_variable("MISSING_TEST_BOOL", True))
        self.assertFalse(bool_environment_variable("MISSING_TEST_BOOL", False))

        os.environ["ANOTHER_TEST_BOOL"] = "True"
        self.assertTrue(bool_environment_variable("ANOTHER_TEST_BOOL", False))
        os.environ["ANOTHER_TEST_BOOL"] = "true"
        self.assertTrue(bool_environment_variable("ANOTHER_TEST_BOOL", False))
        os.environ["ANOTHER_TEST_BOOL"] = "False"
        self.assertFalse(bool_environment_variable("ANOTHER_TEST_BOOL", True))
        os.environ["ANOTHER_TEST_BOOL"] = "false"
        self.assertFalse(bool_environment_variable("ANOTHER_TEST_BOOL", True))
        os.environ["ANOTHER_TEST_BOOL"] = "1"
        self.assertTrue(bool_environment_variable("ANOTHER_TEST_BOOL", False))

    def test_generate_fernet_encryption_key(self):
        key = generate_fernet_encryption_key()
        self.assertIsInstance(key, str)
        self.assertGreaterEqual(len(key), 32)
        # Should be urlsafe base64
        base64.urlsafe_b64decode(key.encode())

    def test_mask_string_basic(self):
        string_length = 12
        masked = mask_string("supersecretpassword", mask_char="*", mask_length=4, string_length=string_length)
        self.assertTrue(masked.endswith("word"))
        self.assertEqual(len(masked), min(len("supersecretpassword"), string_length))

    def test_mask_string_truncate(self):
        masked = mask_string("supersecretpassword", mask_char="#", mask_length=3, string_length=8)
        self.assertEqual(masked, "#####ord")

    def test_mask_string_short(self):
        masked = mask_string("abc", mask_length=4)
        self.assertEqual(masked, "abc")

    def test_mask_string_bytes(self):
        masked = mask_string(b"secret", mask_length=2)
        self.assertTrue(masked.endswith("et"))
