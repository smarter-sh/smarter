"""Test cases for the cache decorators."""

import asyncio
import threading
import time
from dataclasses import dataclass
from unittest.mock import PropertyMock, patch

from smarter.lib.cache import cache_results, lazy_cache
from smarter.lib.cache.lazy_cache import LazyCache
from smarter.lib.unittest.base_classes import SmarterTestBase


@dataclass
class _Point:
    """A dataclass that is not hashable."""

    x: int


class _Alpha:
    """One of two classes whose cached functions share a name."""

    calls = 0

    @staticmethod
    @cache_results(timeout=60)
    def get(x):
        _Alpha.calls += 1
        return f"alpha:{x}"


class _Beta:
    """The other class whose cached function is also named get()."""

    calls = 0

    @staticmethod
    @cache_results(timeout=60)
    def get(x):
        _Beta.calls += 1
        return f"beta:{x}"


class _Shape:
    """A class with a cached classmethod."""

    calls: list = []

    @classmethod
    @cache_results(timeout=60)
    def describe(cls, size):
        _Shape.calls.append((cls.__name__, size))
        return f"{cls.__name__}:{size}"


class _Square(_Shape):
    """A subclass, whose classmethod results are cached apart from its parent's."""


class TestLazyCache(SmarterTestBase):
    """Unit tests for LazyCache wrapper."""

    def test_get_set_delete(self):
        lazy_cache = LazyCache()
        key = "test_key"
        value = "test_value"
        # Ensure clean state
        lazy_cache.delete(key)
        self.assertIsNone(lazy_cache.get(key))
        # set may return True or None depending on backend
        set_result = lazy_cache.set(key, value)
        self.assertIn(set_result, (None, True))
        self.assertEqual(lazy_cache.get(key), value)
        self.assertTrue(lazy_cache.delete(key))
        self.assertIsNone(lazy_cache.get(key))

    def test_incr_decr(self):
        lazy_cache = LazyCache()
        key = "test_incr"
        lazy_cache.delete(key)
        lazy_cache.set(key, 0)
        self.assertEqual(lazy_cache.incr(key), 1)
        self.assertEqual(lazy_cache.decr(key), 0)
        lazy_cache.delete(key)

    def test_add_touch_has_key(self):
        lazy_cache = LazyCache()
        key = "test_add"
        lazy_cache.delete(key)
        added = lazy_cache.add(key, "v")
        if not added:
            lazy_cache.set(key, "v")
        # Try touch, but don't fail if not supported
        touched = lazy_cache.touch(key)
        # Accept both True and False, but always check has_key
        self.assertTrue(lazy_cache.has_key(key))
        lazy_cache.delete(key)

    def test_get_many_set_many_delete_many(self):
        lazy_cache = LazyCache()
        keys = ["a", "b"]
        data = {"a": 1, "b": 2}
        lazy_cache.delete_many(keys)
        self.assertEqual(lazy_cache.get_many(keys), {})  # Should be empty dict if keys don't exist
        lazy_cache.set_many(data)
        self.assertEqual(lazy_cache.get_many(keys), data)
        lazy_cache.delete_many(keys)
        self.assertEqual(lazy_cache.get_many(keys), {})  # Should be empty dict again

    def test_incr_decr_version(self):
        lazy_cache = LazyCache()
        key = "test_version"
        lazy_cache.delete(key)
        lazy_cache.set(key, 0)
        # incr_version should succeed and return a new version number
        version = lazy_cache.incr_version(key)
        self.assertIsInstance(version, int)
        # decr_version may raise ValueError if the key is not found (backend dependent)
        try:
            version2 = lazy_cache.decr_version(key)
            self.assertIsInstance(version2, int)
        except ValueError as e:
            self.assertIn("not found", str(e).lower())
        # If you delete the key, decr_version should raise ValueError
        lazy_cache.delete(key)
        with self.assertRaises(ValueError):
            lazy_cache.decr_version(key)

    def test_clear_close(self):
        lazy_cache = LazyCache()
        # Should not raise
        self.assertIsNone(lazy_cache.clear())
        self.assertIsNone(lazy_cache.close())

    def test_cache_logging_property(self):
        # This test assumes the Waffle switch for CACHE_LOGGING is False by default.
        # If you want to test True, set the switch in your test DB or settings.
        lazy_cache = LazyCache()
        # Should not raise, should return a bool
        result = lazy_cache.cache_logging
        self.assertIsInstance(result, bool)

    def test_cache_property_diagnostics(self):
        # Remove _cache to force re-init and exercise diagnostics
        lazy_cache = LazyCache()
        lazy_cache._cache = None
        # Should not raise and should return a cache object
        result = lazy_cache.cache
        self.assertIsNotNone(result)

    def test_waffle_property_lazy_import(self):
        lazy_cache = LazyCache()
        lazy_cache._waffle = None
        # Should not raise and should return a module
        result = lazy_cache.waffle
        self.assertIsNotNone(result)


class TestCacheResults(SmarterTestBase):
    """Integration tests for the cache_results decorator (no mocks)."""

    def setUp(self):
        # Clear cache before each test to avoid interference
        lazy_cache = LazyCache()
        lazy_cache.clear()

    def test_cache_miss_and_hit(self):
        calls = []

        @cache_results(timeout=60)
        def add(x, y):
            calls.append((x, y))
            return x + y

        # First call: miss
        result1 = add(2, 3)
        self.assertEqual(result1, 5)
        self.assertEqual(len(calls), 1)
        # Second call: hit
        result2 = add(2, 3)
        self.assertEqual(result2, 5)
        self.assertEqual(len(calls), 1)

    def test_cache_with_none_result(self):
        calls = []

        @cache_results(timeout=60)
        def maybe_none(x):
            calls.append(x)
            return None if x == 0 else x

        # Miss, returns None
        self.assertIsNone(maybe_none(0))
        self.assertEqual(len(calls), 1)
        # Hit, still returns None
        self.assertIsNone(maybe_none(0))
        self.assertEqual(len(calls), 1)
        # Miss, returns value
        self.assertEqual(maybe_none(1), 1)
        self.assertEqual(len(calls), 2)

    def test_cache_with_kwargs(self):
        calls = []

        @cache_results(timeout=60)
        def combine(a, b=0):
            calls.append((a, b))
            return a + b

        self.assertEqual(combine(1, b=2), 3)
        self.assertEqual(combine(1, b=2), 3)
        self.assertEqual(len(calls), 1)
        self.assertEqual(combine(1, b=3), 4)
        self.assertEqual(len(calls), 2)

    def test_cache_invalidate(self):
        calls = []

        @cache_results(timeout=60)
        def square(x):
            calls.append(x)
            return x * x

        self.assertEqual(square(4), 16)
        self.assertEqual(square(4), 16)
        self.assertEqual(len(calls), 1)
        square.invalidate(4)
        self.assertEqual(square(4), 16)
        self.assertEqual(len(calls), 2)

    def test_cache_invalidate_cached_none(self):
        """Invalidate() reports a cached None as None, not as the sentinel string that stores it."""
        calls = []

        # an invalidation is logged at INFO only when cache logging is on.
        @cache_results(timeout=60, logging_enabled=True)
        def nothing(x):
            calls.append(x)

        self.assertIsNone(nothing(1))
        self.assertIsNone(nothing(1))
        self.assertEqual(len(calls), 1)
        with self.assertLogs("smarter.lib.cache.decorators", level="INFO") as logs:
            nothing.invalidate(1)
        self.assertIn("invalidated None", "\n".join(logs.output))
        self.assertIsNone(nothing(1))
        self.assertEqual(len(calls), 2)

    def test_cache_invalidate_missing_entry(self):
        """Invalidate() of an entry that is not cached deletes nothing, and logs no invalidation."""

        @cache_results(timeout=60)
        def never_called(x):
            return x

        with patch("smarter.lib.cache.decorators.lazy_cache.delete") as delete:
            never_called.invalidate(1)
        delete.assert_not_called()

    def test_cache_invalidate_reads_once(self):
        """Invalidate() reads the entry once, so that one that expires mid-call is not reported as a cached None."""

        @cache_results(timeout=60)
        def double(x):
            return 2 * x

        double(1)
        with (
            patch("smarter.lib.cache.decorators.lazy_cache.has_key", return_value=True) as has_key,
            patch("smarter.lib.cache.decorators.lazy_cache.get", side_effect=lambda key, default=None: default),
            patch("smarter.lib.cache.decorators.lazy_cache.delete") as delete,
        ):
            double.invalidate(1)
        has_key.assert_not_called()
        delete.assert_not_called()

    def test_cache_different_args(self):
        calls = []

        @cache_results(timeout=60)
        def f(x, y):
            calls.append((x, y))
            return x * y

        self.assertEqual(f(2, 3), 6)
        self.assertEqual(f(3, 2), 6)
        self.assertEqual(len(calls), 2)
        self.assertEqual(f(2, 3), 6)
        self.assertEqual(len(calls), 2)

    def test_cache_invalidate_matches_call_style(self):
        """Invalidate() clears the entry whether arguments are passed positionally, by keyword or by default."""
        calls = []

        @cache_results(timeout=60)
        def lookup(name, class_name="Account"):
            calls.append((name, class_name))
            return f"{class_name}:{name}"

        self.assertEqual(lookup("x"), "Account:x")
        self.assertEqual(lookup("x", class_name="Account"), "Account:x")
        self.assertEqual(lookup(name="x", class_name="Account"), "Account:x")
        self.assertEqual(len(calls), 1)

        lookup.invalidate("x", "Account")
        self.assertEqual(lookup("x"), "Account:x")
        self.assertEqual(len(calls), 2)

    def test_unhashable_argument(self):
        """An argument that can't be hashed, e.g. a dataclass, is cached rather than crashing the call."""
        calls = []

        @cache_results(timeout=60)
        def where(point):
            calls.append(point)
            return point.x

        self.assertEqual(where(_Point(1)), 1)
        self.assertEqual(where(_Point(1)), 1)
        self.assertEqual(len(calls), 1)

    def test_same_name_in_two_classes(self):
        """Functions that share a module and a name, but not a qualified name, don't share cache entries."""
        _Alpha.calls = _Beta.calls = 0
        self.assertEqual(_Alpha.get(1), "alpha:1")
        self.assertEqual(_Beta.get(1), "beta:1")
        self.assertEqual(_Alpha.get(1), "alpha:1")
        self.assertEqual((_Alpha.calls, _Beta.calls), (1, 1))

    def test_instance_method_is_refused(self):
        """Decorating an instance method raises at decoration time, because self would be part of the key."""
        with self.assertRaises(TypeError):

            class _Widget:  # pylint: disable=unused-variable
                """A class with a decorated instance method."""

                @cache_results(timeout=60)
                def size(self, x):
                    return x

    def test_classmethod_is_cached_per_class(self):
        """A classmethod is cached, and a subclass's results are cached apart from its parent's."""
        _Shape.calls = []
        self.assertEqual(_Shape.describe(2), "_Shape:2")
        self.assertEqual(_Shape.describe(2), "_Shape:2")
        self.assertEqual(_Square.describe(2), "_Square:2")
        self.assertEqual(_Square.describe(2), "_Square:2")
        self.assertEqual(_Shape.calls, [("_Shape", 2), ("_Square", 2)])
        _Shape.describe.invalidate(_Shape, 2)
        self.assertEqual(_Shape.describe(2), "_Shape:2")
        self.assertEqual(len(_Shape.calls), 3)

    def test_dict_and_pairs_have_different_keys(self):
        """A dict and a list of its pairs don't share a key, and equal sets share one regardless of order."""
        calls = []

        @cache_results(timeout=60)
        def echo(value):
            calls.append(value)
            return type(value).__name__

        self.assertEqual(echo({"a": 1}), "dict")
        self.assertEqual(echo([("a", 1)]), "list")
        self.assertEqual(echo({"x", "y", "z"}), "set")
        self.assertEqual(echo({"z", "y", "x"}), "set")
        self.assertEqual(echo(["x", "y", "z"]), "list")
        self.assertEqual(len(calls), 4)

    def test_unserializable_argument_runs_uncached(self):
        """Arguments that can't be serialized are not cached: the function runs every time, and an error is logged."""
        calls = []
        circular: list = []
        circular.append(circular)

        @cache_results(timeout=60)
        def length(value):
            calls.append(value)
            return len(value)

        with self.assertLogs("smarter.lib.cache.decorators", level="ERROR"):
            self.assertEqual(length(circular), 1)
        with self.assertLogs("smarter.lib.cache.decorators", level="ERROR"):
            self.assertEqual(length(circular), 1)
        self.assertEqual(len(calls), 2)

    def test_logs_omit_results(self):
        """Cache hit and miss logs name the function and the result's type, never the result."""

        @cache_results(timeout=60, logging_enabled=True)
        def reveal(x):
            return f"do-not-log-{x}"

        with self.assertLogs("smarter.lib.cache.decorators", level="INFO") as logs:
            reveal(1)
            reveal(1)
        output = "\n".join(logs.output)
        self.assertNotIn("do-not-log-1", output)
        self.assertIn("caching str for", output)
        self.assertIn("cache hit for", output)
        self.assertIn("test_logs_omit_results.<locals>.reveal", output)

    def test_before_apps_are_ready(self):
        """Before Django's apps are ready, calls run uncached and invalidate() does nothing, rather than crash."""
        calls = []

        @cache_results(timeout=60)
        def early(x):
            calls.append(x)
            return x

        with (
            patch.object(LazyCache, "ready", new_callable=PropertyMock, return_value=False),
            patch("smarter.lib.cache.decorators.lazy_cache.get") as get,
        ):
            self.assertEqual(early(1), 1)
            self.assertEqual(early(1), 1)
            early.invalidate(1)
        get.assert_not_called()
        self.assertEqual(len(calls), 2)

    def test_async_function(self):
        """An async function's result is cached, rather than its coroutine."""
        calls = []

        @cache_results(timeout=60)
        async def fetch(x):
            calls.append(x)
            return x * 10

        self.assertEqual(asyncio.run(fetch(3)), 30)
        self.assertEqual(asyncio.run(fetch(3)), 30)
        self.assertEqual(len(calls), 1)
        fetch.invalidate(3)
        self.assertEqual(asyncio.run(fetch(3)), 30)
        self.assertEqual(len(calls), 2)

    def test_async_function_before_apps_are_ready(self):
        """Before Django's apps are ready, an async function runs uncached."""
        calls = []

        @cache_results(timeout=60)
        async def fetch_early(x):
            calls.append(x)
            return x

        with patch.object(LazyCache, "ready", new_callable=PropertyMock, return_value=False):
            self.assertEqual(asyncio.run(fetch_early(1)), 1)
            self.assertEqual(asyncio.run(fetch_early(1)), 1)
        self.assertEqual(len(calls), 2)

    def test_concurrent_misses_compute_once(self):
        """Threads that miss the same key at once wait for the first to compute it, rather than all compute it."""
        calls = []
        entered = threading.Event()
        release = threading.Event()

        @cache_results(timeout=60)
        def slow(x):
            calls.append(x)
            entered.set()
            release.wait(5)
            return x

        results = []
        first = threading.Thread(target=lambda: results.append(slow(7)))
        second = threading.Thread(target=lambda: results.append(slow(7)))
        first.start()
        self.assertTrue(entered.wait(5))
        second.start()
        time.sleep(0.2)  # let the second thread reach the lock
        release.set()
        first.join(5)
        second.join(5)
        self.assertEqual(results, [7, 7])
        self.assertEqual(len(calls), 1)

    def test_verbose_logs_omit_results(self):
        """Verbose cache logging adds the arguments, but still never the result."""

        @cache_results(timeout=60, logging_enabled=True)
        def reveal_verbose(x):
            return f"do-not-log-{x}"

        with (
            patch.object(lazy_cache, "verbose_logging", True),
            self.assertLogs("smarter.lib.cache.decorators", level="INFO") as logs,
        ):
            reveal_verbose(2)
            reveal_verbose(2)
        output = "\n".join(logs.output)
        self.assertNotIn("do-not-log-2", output)
        self.assertIn("args: (2,)", output)

    def test_explicit_cache_key(self):
        """A decorator's cache_key is used for every call, and invalidate() clears it."""
        calls = []

        @cache_results(timeout=60, cache_key=f"test_explicit_cache_key_{self.hash_suffix}")
        def constant():
            calls.append(1)
            return "constant"

        self.assertEqual(constant(), "constant")
        self.assertEqual(constant(), "constant")
        self.assertEqual(len(calls), 1)
        constant.invalidate()
        self.assertEqual(constant(), "constant")
        self.assertEqual(len(calls), 2)

    def test_invalidate_unserializable_argument(self):
        """Invalidate() with arguments that can't be serialized deletes nothing."""
        circular: list = []
        circular.append(circular)

        @cache_results(timeout=60)
        def length_again(value):
            return len(value)

        with (
            self.assertLogs("smarter.lib.cache.decorators", level="ERROR"),
            patch("smarter.lib.cache.decorators.lazy_cache.delete") as delete,
        ):
            length_again.invalidate(circular)
        delete.assert_not_called()
