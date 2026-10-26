"""Test cases for smarter.lib.cache.hooks, Smarter's hooks for the cache-results package."""

from unittest.mock import patch

from cache_results import CacheKeyArgumentError, cache_results, lazy_cache
from cache_results.colors import DEFAULT_COLORS
from cache_results.conf import cache_results_settings
from cache_results.keys import dumps
from pydantic import BaseModel, HttpUrl

from smarter.common.conf import smarter_settings
from smarter.lib.cache import hooks
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest.base_classes import SmarterTestBase


class _Query(BaseModel):
    """A Pydantic model, as a cache key argument."""

    text: str
    limit: int = 10


class TestHooks(SmarterTestBase):
    """Test the logging hooks and SmarterCacheKeyEncoder."""

    def test_logging_enabled_follows_the_switch(self):
        """Logging follows the CACHE_LOGGING waffle switch."""
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=True) as is_active:
            self.assertTrue(hooks.logging_enabled())
        is_active.assert_called_once_with(SmarterWaffleSwitches.CACHE_LOGGING)
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            self.assertFalse(hooks.logging_enabled())

    def test_verbose_logging_follows_settings(self):
        """Verbose logging follows smarter_settings.verbose_logging."""
        self.assertEqual(hooks.verbose_logging(), bool(smarter_settings.verbose_logging))

    def test_encoder_accepts_pydantic(self):
        """Urls are encoded as text, and models by their class and JSON dump."""
        encoder = hooks.SmarterCacheKeyEncoder
        self.assertEqual(dumps(HttpUrl("https://example.com/a"), encoder), '"https://example.com/a"')
        self.assertEqual(
            dumps(_Query(text="x"), encoder),
            f'{{"__model__":"{__name__}._Query","fields":{{"limit":10,"text":"x"}}}}',
        )
        self.assertNotEqual(dumps(_Query(text="x"), encoder), dumps(_Query(text="y"), encoder))

    def test_encoder_still_refuses_objects(self):
        """Other objects are still refused."""
        with self.assertRaises(CacheKeyArgumentError):
            dumps(object(), hooks.SmarterCacheKeyEncoder)


class TestSmarterConfiguration(SmarterTestBase):
    """Test that the cache-results package runs with Smarter's CACHE_RESULTS setting and hooks."""

    def setUp(self):
        lazy_cache.clear()

    def test_settings_name_smarter_hooks(self):
        """The CACHE_RESULTS setting names Smarter's encoder, default timeout and logging hooks."""
        self.assertEqual(cache_results_settings.cache_alias, "default")
        self.assertIs(cache_results_settings.key_encoder, hooks.SmarterCacheKeyEncoder)
        self.assertEqual(cache_results_settings.timeout, smarter_settings.cache_expiration)
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=True):
            self.assertTrue(cache_results_settings.logging_enabled)
        self.assertEqual(cache_results_settings.verbose_logging, bool(smarter_settings.verbose_logging))
        self.assertIn(DEFAULT_COLORS["hit"], cache_results_settings.log_prefix("p", "hit"))

    def test_pydantic_arguments_are_cached(self):
        """A Pydantic model is a cache key argument, keyed by its fields, in Smarter's cache."""
        calls = []

        @cache_results(timeout=60)
        def search(query: _Query) -> str:
            calls.append(query)
            return query.text.upper()

        self.assertEqual(search(_Query(text="x")), "X")
        self.assertEqual(search(_Query(text="x")), "X")
        self.assertEqual(search(_Query(text="y")), "Y")
        self.assertEqual(len(calls), 2)
        search.invalidate(_Query(text="x"))
        search(_Query(text="x"))
        self.assertEqual(len(calls), 3)

    def test_logs_through_hooks(self):
        """With the CACHE_LOGGING switch on, misses and hits are logged with colored prefixes."""

        @cache_results(timeout=60)
        def logged(x: int) -> int:
            return x

        with (
            patch("smarter.lib.django.waffle.switch_is_active", return_value=True),
            self.assertLogs("cache_results.decorators", level="INFO") as logs,
        ):
            logged(1)
            logged(1)
        output = "\n".join(logs.output)
        self.assertIn(DEFAULT_COLORS["miss"], output)
        self.assertIn(DEFAULT_COLORS["hit"], output)
