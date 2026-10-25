"""Test cases for smarter.lib.cache.keys, the cache keys of @cache_results."""

import datetime
import decimal
import uuid
from dataclasses import dataclass

from smarter.lib.cache.keys import (
    CacheKeyArgumentError,
    CacheKeyEncoder,
    bind_arguments,
    describe_key_error,
    dumps,
    make_key,
    normalize,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


@dataclass(frozen=True)
class _Range:
    """A frozen dataclass, as a value object argument."""

    low: int
    high: int


class _Opaque:
    """An object with no safe cache key."""

    def __str__(self):
        return "opaque-value"


def _lookup(name, class_name="Account"):
    """A function to make keys for."""
    return f"{class_name}:{name}"


class TestCacheKeyEncoder(SmarterTestBase):
    """Test CacheKeyEncoder, which serializes known types and refuses the rest."""

    def test_canonical_output(self):
        """The output is compact, with sorted keys."""
        self.assertEqual(dumps({"b": 1, "a": [1, 2]}), '{"a":[1,2],"b":1}')

    def test_known_types(self):
        """Datetimes, Decimals and UUIDs are encoded as DjangoJSONEncoder encodes them."""
        self.assertEqual(dumps(datetime.datetime(2026, 1, 2, 3, 4, 5)), '"2026-01-02T03:04:05"')
        self.assertEqual(dumps(decimal.Decimal("1.50")), '"1.50"')
        value = uuid.UUID("12345678-1234-5678-1234-567812345678")
        self.assertEqual(dumps(value), f'"{value}"')

    def test_unknown_type_is_refused(self):
        """An object is refused, with its type but not its value in the message."""
        with self.assertRaises(CacheKeyArgumentError) as context:
            dumps(_Opaque())
        self.assertIn("_Opaque", str(context.exception))
        self.assertNotIn("opaque-value", str(context.exception))
        self.assertIsInstance(context.exception, TypeError)

    def test_refused_values_raise(self):
        """Values the encoder refuses, such as a timezone-aware time, raise ValueError."""
        with self.assertRaises(ValueError):
            dumps(datetime.time(3, 4, 5, tzinfo=datetime.timezone.utc))

    def test_subclass_adds_a_type(self):
        """A subclass of the encoder can accept another type."""

        class _OpaqueEncoder(CacheKeyEncoder):
            def default(self, o):
                if isinstance(o, _Opaque):
                    return "opaque"
                return super().default(o)

        self.assertEqual(dumps(_Opaque(), _OpaqueEncoder), '"opaque"')


class TestNormalize(SmarterTestBase):
    """Test normalize(), which makes equal arguments serialize the same."""

    def test_sets_are_sorted_and_tagged(self):
        """Equal sets normalize the same, whatever their order, and differently from a list."""
        self.assertEqual(normalize({"z", "x", "y"}), {"__set__": ["x", "y", "z"]})
        self.assertEqual(normalize(frozenset({3, 1, 2})), {"__set__": [1, 2, 3]})
        self.assertNotEqual(dumps(normalize({1, 2})), dumps(normalize([1, 2])))

    def test_tuples_and_dicts(self):
        """Tuples become lists, and dicts stay dicts, recursively."""
        self.assertEqual(normalize({"a": (1, {"b": {2}})}), {"a": [1, {"b": {"__set__": [2]}}]})

    def test_classes(self):
        """A class is identified by its module and qualified name."""
        self.assertEqual(normalize(_Range), {"__class__": f"{__name__}._Range"})

    def test_dataclasses(self):
        """A dataclass is identified by its class and fields."""
        self.assertEqual(
            normalize(_Range(1, 5)),
            {"__dataclass__": f"{__name__}._Range", "fields": {"low": 1, "high": 5}},
        )

    def test_set_of_unknown_objects_is_refused(self):
        """A set member that can't be serialized is refused while sorting."""
        with self.assertRaises(CacheKeyArgumentError):
            normalize({_Opaque(), _Opaque()})


class TestMakeKey(SmarterTestBase):
    """Test make_key(), bind_arguments() and describe_key_error()."""

    def test_key_names_the_function(self):
        """A key is the prefix, module, qualified name and a 32-character hash."""
        key = make_key(_lookup, ("x",), {}, prefix="v2:")
        self.assertTrue(key.startswith(f"v2:{__name__}._lookup()_"))
        self.assertEqual(len(key.rsplit("_", 1)[1]), 32)

    def test_call_styles_share_a_key(self):
        """Positional, keyword and default arguments produce the same key."""
        self.assertEqual(make_key(_lookup, ("x",), {}), make_key(_lookup, (), {"name": "x", "class_name": "Account"}))

    def test_different_arguments_have_different_keys(self):
        """Different arguments produce different keys."""
        self.assertNotEqual(make_key(_lookup, ("x",), {}), make_key(_lookup, ("y",), {}))

    def test_arguments_that_dont_fit_the_signature(self):
        """Arguments that don't bind to the signature are used as they are."""
        self.assertEqual(bind_arguments(_lookup, (1, 2, 3), {}), ((1, 2, 3), {}))
        self.assertEqual(bind_arguments(_lookup, ("x",), {}), ((), {"name": "x", "class_name": "Account"}))

    def test_refused_argument(self):
        """An argument that can't be part of a key raises CacheKeyArgumentError."""
        with self.assertRaises(CacheKeyArgumentError):
            make_key(_lookup, (_Opaque(),), {})

    def test_describe_key_error(self):
        """Errors are described without argument values."""
        self.assertIn("nested too deeply", describe_key_error(RecursionError()))
        self.assertEqual(
            describe_key_error(ValueError("Circular reference detected")), "ValueError: Circular reference detected"
        )
        self.assertIn("plain values", describe_key_error(CacheKeyArgumentError("plain values")))
