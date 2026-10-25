"""Test cases for smarter.lib.cache.hooks, Smarter's configuration of @cache_results."""

from unittest.mock import patch

from pydantic import BaseModel, HttpUrl

from smarter.common.helpers.console_helpers import SmarterFormattedTextColorCodes
from smarter.lib.cache import hooks, lazy_cache
from smarter.lib.cache.keys import CacheKeyArgumentError, dumps
from smarter.lib.unittest.base_classes import SmarterTestBase


class _Query(BaseModel):
    """A Pydantic model, as a cache key argument."""

    text: str
    limit: int = 10


class TestHooks(SmarterTestBase):
    """Test the logging hooks and SmarterCacheKeyEncoder."""

    def test_logging_hooks_follow_lazy_cache(self):
        """Logging follows the CACHE_LOGGING waffle switch, through lazy_cache."""
        with patch.object(lazy_cache, "cache_logging", True), patch.object(lazy_cache, "verbose_logging", False):
            self.assertTrue(hooks.logging_enabled())
            self.assertFalse(hooks.verbose_logging())

    def test_log_prefix_colors(self):
        """Hits are green, misses red, invalidations gray, and other messages uncolored."""
        self.assertIn(SmarterFormattedTextColorCodes.REGULAR_GREEN, hooks.log_prefix("p", "hit"))
        self.assertIn(SmarterFormattedTextColorCodes.DARK_RED, hooks.log_prefix("p", "miss"))
        self.assertIn(SmarterFormattedTextColorCodes.LIGHT_GRAY, hooks.log_prefix("p", "invalidate"))
        self.assertIn("p", hooks.log_prefix("p", ""))

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
