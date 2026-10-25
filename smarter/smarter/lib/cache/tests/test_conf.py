"""Test cases for smarter.lib.cache.conf, the CACHE_RESULTS setting."""

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.test import override_settings

from smarter.lib.cache.conf import cache_results_settings
from smarter.lib.cache.hooks import SmarterCacheKeyEncoder
from smarter.lib.cache.keys import CacheKeyEncoder
from smarter.lib.unittest.base_classes import SmarterTestBase


def _always() -> bool:
    """A LOGGING_ENABLED hook that is always on."""
    return True


def _shout(text: str, event: str) -> str:
    """A LOG_PREFIX hook."""
    return f"{text.upper()}[{event}]"


class TestCacheResultsSettings(SmarterTestBase):
    """Test CacheResultsSettings, with and without a CACHE_RESULTS setting."""

    @override_settings(CACHE_RESULTS=None)
    def test_defaults(self):
        """Without the setting, results use the default cache, its timeout, no prefix, the strict encoder and no logs."""
        self.assertEqual(cache_results_settings.cache_alias, "default")
        self.assertIs(cache_results_settings.timeout, DEFAULT_TIMEOUT)
        self.assertEqual(cache_results_settings.key_prefix, "")
        self.assertIs(cache_results_settings.key_encoder, CacheKeyEncoder)
        self.assertFalse(cache_results_settings.logging_enabled)
        self.assertFalse(cache_results_settings.verbose_logging)
        self.assertEqual(cache_results_settings.log_prefix("prefix", "hit"), "prefix")

    def test_smarter_settings(self):
        """Smarter's settings name its hooks and its encoder."""
        self.assertIs(cache_results_settings.key_encoder, SmarterCacheKeyEncoder)
        self.assertIsInstance(cache_results_settings.timeout, int)
        self.assertIsInstance(cache_results_settings.logging_enabled, bool)

    @override_settings(CACHE_RESULTS={"KEY_PREFIX": "app:", "VERSION": 3, "TIMEOUT": 10, "CACHE_ALIAS": "results"})
    def test_values(self):
        """Prefix and version start every key, and the alias and timeout are used as given."""
        self.assertEqual(cache_results_settings.key_prefix, "app:v3:")
        self.assertEqual(cache_results_settings.timeout, 10)
        self.assertEqual(cache_results_settings.cache_alias, "results")

    @override_settings(CACHE_RESULTS={"VERSION": 0})
    def test_version_zero(self):
        """A version of 0 is still a version."""
        self.assertEqual(cache_results_settings.key_prefix, "v0:")

    def test_hooks_as_objects_dotted_paths_and_flags(self):
        """Hooks are given as objects, as dotted paths, or as plain flags."""
        with override_settings(CACHE_RESULTS={"LOGGING_ENABLED": _always, "VERBOSE_LOGGING": True}):
            self.assertTrue(cache_results_settings.logging_enabled)
            self.assertTrue(cache_results_settings.verbose_logging)
        with override_settings(
            CACHE_RESULTS={"LOGGING_ENABLED": f"{__name__}._always", "LOG_PREFIX": f"{__name__}._shout"}
        ):
            self.assertTrue(cache_results_settings.logging_enabled)
            self.assertEqual(cache_results_settings.log_prefix("prefix", "miss"), "PREFIX[miss]")
        with override_settings(CACHE_RESULTS={"KEY_ENCODER": SmarterCacheKeyEncoder}):
            self.assertIs(cache_results_settings.key_encoder, SmarterCacheKeyEncoder)

    @override_settings(CACHE_RESULTS={"KEY_ENCODER": "json.JSONEncoder"})
    def test_key_encoder_must_be_a_cache_key_encoder(self):
        """An encoder that isn't a CacheKeyEncoder, which would not refuse unsafe arguments, is refused."""
        with self.assertRaises(TypeError):
            _ = cache_results_settings.key_encoder
