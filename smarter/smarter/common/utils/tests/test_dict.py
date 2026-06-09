"""Test utility functions."""

from smarter.common.utils import (
    dict_is_contained_in,
    dict_is_subset,
    recursive_sort_dict,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestDictionaryUtils(SmarterTestBase):
    """Test dictionary utility functions."""

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

    def test_dict_is_subset_true(self):
        big = {
            "name": "Alice",
            "profile": {"age": 30, "city": "Wonderland"},
            "roles": ["admin", "user"],
        }
        small = {"profile": {"age": 30}, "roles": ["admin"]}
        self.assertTrue(dict_is_subset(small, big))

    def test_dict_is_subset_false(self):
        big = {"profile": {"age": 30, "city": "Wonderland"}, "roles": ["admin", "user"]}
        small = {"profile": {"age": 31}}
        self.assertFalse(dict_is_subset(small, big))
