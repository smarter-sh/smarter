"""Test :class:`smarter.common.mixins.helper_mixin.SmarterHelperMixin`."""

import os
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.http import HttpRequest

from smarter.common.exceptions import SmarterValueError
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.unittest.base_classes import SmarterTestBase


class Helper(SmarterHelperMixin):
    """A plain subclass of the mixin."""


class TestSmarterHelperMixin(SmarterTestBase):
    """Test the mixin's helpers, which mostly delegate to smarter.common.utils."""

    def setUp(self):
        super().setUp()
        self.helper = Helper()

    def test_names_and_states(self):
        self.assertEqual(self.helper.unformatted_class_name, "Helper")
        self.assertIn("Helper", self.helper.formatted_class_name)
        self.assertTrue(self.helper.ready)
        self.assertNotEqual(self.helper.formatted_state_ready, self.helper.formatted_state_not_ready)

    def test_amnesty(self):
        self.assertEqual(self.helper.health_check_urls, ["readiness", "healthz"])
        self.assertIn("favicon.ico", self.helper.amnesty_urls)
        self.assertTrue(self.helper.deserves_amnesty("/healthz/"))
        self.assertTrue(self.helper.deserves_amnesty("robots.txt"))
        self.assertFalse(self.helper.deserves_amnesty("/api/v1/cli/whoami/"))

    def test_smarter_build_absolute_uri(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "testserver"
        request.path = "/a/"
        self.assertEqual(self.helper.smarter_build_absolute_uri(request), "http://testserver/a/")

    def test_smarter_build_absolute_uri_per_request(self):
        """Test that each request's url is returned, e.g. by a long-lived middleware, not the first request's."""
        first = HttpRequest()
        first.META["HTTP_HOST"] = "testserver"
        first.path = "/dashboard/"
        second = HttpRequest()
        second.META["HTTP_HOST"] = "testserver"
        second.path = "/api/v1/cli/whoami/"
        self.assertEqual(self.helper.smarter_build_absolute_uri(first), "http://testserver/dashboard/")
        self.assertEqual(self.helper.smarter_build_absolute_uri(second), "http://testserver/api/v1/cli/whoami/")

    def test_formatting(self):
        for method in (
            self.helper.formatted_text,
            self.helper.formatted_text_green,
            self.helper.formatted_text_red,
            self.helper.formatted_text_blue,
        ):
            with self.subTest(method=method.__name__):
                self.assertIn("hello", method("hello"))
        self.assertIn("key", self.helper.formatted_json({"key": "value"}))
        self.assertNotIn("secret-value", self.helper.mask_string("secret-value"))

    def test_bool_environment_variable(self):
        with patch.dict(os.environ, {"SMARTER_TEST_BOOL": "true"}):
            self.assertTrue(self.helper.bool_environment_variable("SMARTER_TEST_BOOL"))
        self.assertTrue(self.helper.bool_environment_variable("SMARTER_TEST_BOOL_MISSING", default=True))

    def test_generate_fernet_encryption_key(self):
        key = self.helper.generate_fernet_encryption_key()
        Fernet(key)  # a valid key

    def test_data_to_dict(self):
        self.assertEqual(self.helper.data_to_dict({"a": 1}), {"a": 1})
        self.assertEqual(self.helper.data_to_dict('{"a": 1}'), {"a": 1})
        self.assertEqual(self.helper.data_to_dict("a: 1"), {"a": 1})
        with self.assertRaises(SmarterValueError):
            self.helper.data_to_dict("a: [1")
        with self.assertRaises(SmarterValueError):
            self.helper.data_to_dict(42)  # type: ignore[arg-type]

    def test_dicts(self):
        self.assertEqual(list(self.helper.sorted_dict({"b": 1, "a": 2}).keys()), ["a", "b"])
        self.assertTrue(self.helper.dict_is_contained_in({"a": 1}, {"a": 1, "b": 2}))
        self.assertTrue(self.helper.dict_is_subset({"a": 1}, {"a": 1, "b": 2}))
        self.assertFalse(self.helper.dict_is_subset({"a": 2}, {"a": 1, "b": 2}))
        self.assertEqual(list(self.helper.recursive_sort_dict({"b": {"d": 1, "c": 2}, "a": 1})["b"].keys()), ["c", "d"])

    def test_files(self):
        with patch("smarter.common.mixins.helper_mixin.utils_get_readonly_csv_file", return_value="csv") as csv_file:
            self.assertEqual(self.helper.get_readonly_csv_file("a.csv"), "csv")
        csv_file.assert_called_once_with("a.csv")
        with patch(
            "smarter.common.mixins.helper_mixin.utils_get_readonly_yaml_file", return_value={"a": 1}
        ) as yaml_file:
            self.assertEqual(self.helper.get_readonly_yaml_file("a.yaml"), {"a": 1})
        yaml_file.assert_called_once_with("a.yaml")

    def test_case_conversion(self):
        self.assertEqual(self.helper.to_snake_case("camelCase"), "camel_case")
        self.assertEqual(self.helper.to_camel_case("snake_case"), "snakeCase")
        self.assertEqual(self.helper.rfc1034_compliant_str("My_Name"), "my-name")
        self.assertEqual(self.helper.rfc1034_compliant_to_snake("my-name"), "my_name")
