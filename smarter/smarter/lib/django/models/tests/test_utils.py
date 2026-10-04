"""Test :mod:`smarter.lib.django.models.utils`."""

from smarter.lib.django.models.utils import (
    dict_key_cleaner,
    dict_keys_to_list,
    list_of_dicts_to_dict,
    list_of_dicts_to_list,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestModelUtils(SmarterTestBase):
    """Test the dict and list helpers."""

    def test_dict_key_cleaner(self):
        self.assertEqual(dict_key_cleaner(" a key\n\r\t"), "_a_key")
        self.assertEqual(dict_key_cleaner(1), "1")  # type: ignore[arg-type]

    def test_dict_keys_to_list(self):
        self.assertEqual(dict_keys_to_list({"a": 1, "b": {"c": 2, "d": {"e": 3}}}), ["a", "b", "c", "d", "e"])
        self.assertEqual(dict_keys_to_list({}), [])

    def test_list_of_dicts_to_list(self):
        """Test that each dict's value of the first dict's first key is returned, cleaned."""
        data = [{"name": "first one", "x": 1}, {"name": "second"}, {"other": "skipped"}]
        self.assertEqual(list_of_dicts_to_list(data), ["first_one", "second"])
        self.assertIsNone(list_of_dicts_to_list([]))
        self.assertIsNone(list_of_dicts_to_list(["not a dict"]))  # type: ignore[list-item]

    def test_list_of_dicts_to_dict(self):
        data = [{"name": "first one"}, {"name": "second"}, {"other": "skipped"}]
        self.assertEqual(list_of_dicts_to_dict(data), {"first_one": "first one", "second": "second"})
        self.assertIsNone(list_of_dicts_to_dict([]))
        self.assertIsNone(list_of_dicts_to_dict([1]))  # type: ignore[list-item]
