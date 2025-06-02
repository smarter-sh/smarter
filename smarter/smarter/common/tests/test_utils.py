"""Test utility functions."""

import json
import os
import tempfile
from datetime import datetime

import yaml
from pydantic import SecretStr

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..utils import (
    DateTimeEncoder,
    camel_to_snake,
    camel_to_snake_dict,
    dict_is_contained_in,
    get_readonly_csv_file,
    get_readonly_yaml_file,
    recursive_sort_dict,
)


class TestUtils(SmarterTestBase):
    """Test utility functions."""

    def test_get_readonly_yaml_file(self):
        data = {"foo": "bar"}
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            f.seek(0)
            path = f.name
        try:
            result = get_readonly_yaml_file(path)
            self.assertEqual(result, data)
        finally:
            os.remove(path)

    def test_get_readonly_csv_file(self):
        csv_content = "a,b\n1,2\n3,4\n"
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write(csv_content)
            f.flush()
            f.seek(0)
            path = f.name
        try:
            result = get_readonly_csv_file(path)
            self.assertEqual(result, [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}])
        finally:
            os.remove(path)

    def test_datetime_encoder(self):
        data = {"date": datetime(2024, 1, 1), "secret": SecretStr("abc")}
        encoded = json.dumps(data, cls=DateTimeEncoder)
        self.assertIn("2024-01-01", encoded)
        self.assertIn("*** REDACTED ***", encoded)

    def test_camel_to_snake(self):
        self.assertEqual(camel_to_snake("camelCase"), "camel_case")
        self.assertEqual(camel_to_snake("CamelCase"), "camel_case")
        self.assertEqual(camel_to_snake("Camel Case"), "camel_case")
        self.assertEqual(camel_to_snake("MYEverlastingSUPERDUPERGobstopper"), "my_everlasting_superduper_gobstopper")
        self.assertEqual(camel_to_snake("already_snake_case"), "already_snake_case")
        self.assertEqual(camel_to_snake(""), "")

    def test_camel_to_snake_dict(self):
        d = {"camelCase": 1, "nestedDict": {"innerKey": 2}}
        result = camel_to_snake_dict(d)
        self.assertIn("camel_case", result)
        self.assertIn("nested_dict", result)
        self.assertIn("inner_key", result["nested_dict"])

    def test_recursive_sort_dict(self):
        d = {"b": 2, "a": {"d": 4, "c": 3}}
        sorted_d = recursive_sort_dict(d)
        self.assertEqual(list(sorted_d.keys()), ["a", "b"])
        self.assertEqual(list(sorted_d["a"].keys()), ["c", "d"])

    def test_dict_is_contained_in_true(self):
        d1 = {"a": 1, "b": {"c": 2}}
        d2 = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        self.assertTrue(dict_is_contained_in(d1, d2))

    def test_dict_is_contained_in_false(self):
        d1 = {"a": 1, "b": {"c": 999}}
        d2 = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        self.assertFalse(dict_is_contained_in(d1, d2))
