"""Test :mod:`smarter.common.conf.util`: the helpers that read fields' defaults and derive defaults."""

import logging
from unittest import TestCase

from smarter.common.conf.settings import Settings
from smarter.common.conf.settings.cache import CacheSettings
from smarter.common.conf.settings.security import generated_django_secret_key
from smarter.common.conf.util import (
    field_default,
    has_field,
    input_value,
    is_unset,
    with_derived_default,
)


class TestFieldDefault(TestCase):
    """A field's default is read from its declaration, and a factory's default is made."""

    def test_declared_default(self):
        self.assertEqual(field_default(Settings, "platform_root_domain"), "example.com")
        self.assertEqual(field_default(Settings, "log_level"), logging.INFO)

    def test_factory_default(self):
        self.assertIs(field_default(Settings, "django_secret_key"), generated_django_secret_key())


class TestHasField(TestCase):
    """A group of fields' validator checks for a field of another group before it reads it."""

    def test_the_settings_class_has_every_group_s_fields(self):
        self.assertTrue(has_field(Settings, "environment"))
        self.assertTrue(has_field(Settings, "subsystem_redis_password"))

    def test_a_group_alone_lacks_the_other_groups_fields(self):
        self.assertTrue(has_field(CacheSettings, "subsystem_redis_password"))
        self.assertFalse(has_field(CacheSettings, "environment"))

    def test_an_instance_is_read_as_its_class(self):
        settings = Settings()
        self.assertTrue(has_field(settings, "environment"))
        self.assertFalse(has_field(settings, "no_such_field"))


class TestDerivedDefaults(TestCase):
    """The helpers of the model validators that derive a default from another field."""

    def test_is_unset(self):
        self.assertTrue(is_unset({}, "a"))
        self.assertTrue(is_unset({"a": None}, "a"))
        self.assertTrue(is_unset({"a": ""}, "a"))
        self.assertTrue(is_unset({"a": "null"}, "a"))
        self.assertFalse(is_unset({"a": "value"}, "a"))
        self.assertFalse(is_unset({"a": 0}, "a"))
        self.assertFalse(is_unset("not a dict", "a"))

    def test_input_value(self):
        self.assertEqual(
            input_value(Settings, {"platform_root_domain": "smarter.sh"}, "platform_root_domain"), "smarter.sh"
        )
        self.assertEqual(input_value(Settings, {}, "platform_root_domain"), "example.com")

    def test_with_derived_default(self):
        data = {"a": 1}
        derived = with_derived_default(data, "b", 2)
        self.assertEqual(derived, {"a": 1, "b": 2})
        self.assertEqual(data, {"a": 1})
        given = {"b": 3}
        self.assertIs(with_derived_default(given, "b", 2), given)
        self.assertEqual(with_derived_default("not a dict", "b", 2), "not a dict")
