"""Test :mod:`smarter.lib.json`, and its SmarterJSONEncoder."""

import datetime
import decimal
import uuid

from smarter.lib import json
from smarter.lib.json import SmarterJSONEncoder, duration_iso_string, is_aware
from smarter.lib.unittest.base_classes import SmarterTestBase


def encode(value):
    return SmarterJSONEncoder().default(value)


class TestSmarterJSONEncoder(SmarterTestBase):
    """Test how the encoder serializes the types that json can't."""

    def test_datetime(self):
        self.assertEqual(encode(datetime.datetime(2026, 1, 2, 3, 4, 5)), "2026-01-02T03:04:05")
        self.assertEqual(
            encode(datetime.datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=datetime.timezone.utc)),
            "2026-01-02T03:04:05.123Z",
        )

    def test_date_and_time(self):
        self.assertEqual(encode(datetime.date(2026, 1, 2)), "2026-01-02")
        self.assertEqual(encode(datetime.time(3, 4, 5)), "03:04:05")
        self.assertEqual(encode(datetime.time(3, 4, 5, 123456)), "03:04:05.123")
        with self.assertRaises(ValueError):
            encode(datetime.time(3, 4, 5, tzinfo=datetime.timezone.utc))

    def test_timedelta(self):
        self.assertEqual(encode(datetime.timedelta(days=1, hours=2, minutes=3, seconds=4)), "P1DT02H03M04S")
        self.assertEqual(duration_iso_string(datetime.timedelta(seconds=-1.5)), "-P0DT00H00M01.500000S")

    def test_scalars(self):
        value = uuid.uuid4()
        self.assertEqual(encode(value), str(value))
        self.assertEqual(encode(decimal.Decimal("1.50")), "1.50")
        self.assertEqual(sorted(encode({1, 2})), [1, 2])

    def test_json_types_are_not_encoded(self):
        """Test that the encoder defers to json for the types that json serializes itself."""
        with self.assertRaises(TypeError):
            encode("a string")

    def test_unknown_type(self):
        with self.assertRaises(TypeError):
            encode(object())

    def test_http_url(self):
        from pydantic import HttpUrl  # pylint: disable=import-outside-toplevel

        self.assertEqual(encode(HttpUrl("https://example.com/a")), "https://example.com/a")

    def test_is_aware(self):
        self.assertTrue(is_aware(datetime.datetime.now(datetime.timezone.utc)))
        self.assertFalse(is_aware(datetime.datetime.now()))

    def test_tagged_item_and_managers(self):
        """Test that taggit's TaggedItem and TaggableManager, and generic relations, are serialized as lists of names."""

        tag = type("Tag", (), {"__module__": "taggit.models", "name": "pii"})()
        self.assertEqual(encode(tag), "pii")
        tagged_item = type("TaggedItem", (), {"__module__": "taggit.models", "tag": tag})()
        self.assertEqual(encode(tagged_item), "pii")

        values = type("Values", (), {"values_list": lambda self, *args, **kwargs: ["a", "b"]})()
        manager = type("_TaggableManager", (), {"__module__": "taggit.managers", "all": lambda self: values})()
        self.assertEqual(encode(manager), ["a", "b"])

        related = type(
            "GenericRelatedObjectManager",
            (),
            {"__module__": "django.contrib.contenttypes.fields", "all": lambda self: [1, 2]},
        )()
        self.assertEqual(encode(related), [1, 2])


class TestDumps(SmarterTestBase):
    """Test smarter.lib.json.dumps(), whose defaults differ from json.dumps()."""

    def test_defaults(self):
        """Test that dumps() indents by 2, and uses the SmarterJSONEncoder."""
        self.assertEqual(json.dumps({"a": 1}), '{\n  "a": 1\n}')
        self.assertEqual(json.loads(json.dumps({"when": datetime.date(2026, 1, 2)})), {"when": "2026-01-02"})

    def test_unknown_type_falls_back_to_str(self):
        """Test that a type that the encoder can't serialize falls back to str()."""

        class Thing:
            def __str__(self):
                return "a thing"

        self.assertEqual(json.loads(json.dumps({"thing": Thing()})), {"thing": "a thing"})

    def test_indent_zero(self):
        self.assertEqual(json.dumps({"a": 1}, indent=0), '{\n"a": 1\n}')

    def test_options(self):
        self.assertEqual(
            json.dumps({"b": 1, "a": 2}, indent=1, sort_keys=True, separators=(",", ":")), '{\n "a":2,\n "b":1\n}'
        )
