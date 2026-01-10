"""Test cases for the cache decorators."""

from smarter.lib.cache import LazyCache, cache_results
from smarter.lib.unittest.base_classes import SmarterTestBase


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
