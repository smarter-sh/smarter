"""Test :mod:`smarter.lib.django.models.utils`."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from smarter.lib.django.models.utils import (
    assign_changed_fields,
    dict_key_cleaner,
    dict_keys_to_list,
    list_of_dicts_to_dict,
    list_of_dicts_to_list,
    tags_changed,
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


class TestAssignChangedFields(SmarterTestBase):
    """Test :func:`assign_changed_fields` and :func:`tags_changed`."""

    def test_only_changed_fields_are_set_and_returned(self):
        instance = SimpleNamespace(name="a", priority=10, config={"x": 1})
        changed = assign_changed_fields(instance, {"name": "a", "priority": 20, "config": {"x": 1}})  # type: ignore[arg-type]
        self.assertEqual(changed, ["priority"])
        self.assertEqual(instance.priority, 20)

    def test_nothing_changed(self):
        instance = SimpleNamespace(name="a", tags=None)
        self.assertEqual(assign_changed_fields(instance, {"name": "a"}), [])  # type: ignore[arg-type]

    def test_a_value_of_another_type_counts_as_changed(self):
        """A float and a Decimal compare unequal, so the instance is saved, as it always was."""
        instance = SimpleNamespace(cost=Decimal("0.1"))
        self.assertEqual(assign_changed_fields(instance, {"cost": 0.1}), ["cost"])  # type: ignore[arg-type]

    def test_a_missing_attribute_is_set(self):
        instance = SimpleNamespace()
        self.assertEqual(assign_changed_fields(instance, {"name": "a"}), ["name"])  # type: ignore[arg-type]
        self.assertEqual(instance.name, "a")

    def test_tags_changed(self):
        instance = MagicMock(pk=1)
        instance.tags.names.return_value = ["a", "b"]
        self.assertFalse(tags_changed(instance, ["b", "a"]))
        self.assertTrue(tags_changed(instance, ["a"]))
        instance.tags.names.return_value = []
        self.assertFalse(tags_changed(instance, None))

    def test_tags_changed_for_a_new_instance(self):
        self.assertTrue(tags_changed(MagicMock(pk=None), []))
