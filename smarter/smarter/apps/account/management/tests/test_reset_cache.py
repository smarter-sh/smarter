"""Test the reset_cache management command."""

from unittest.mock import patch

from django.core.management.base import CommandError

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.reset_cache"


class TestResetCache(CommandTestBase):
    """The cache is patched, so that the command doesn't clear the cache that other tests share."""

    def test_reset_cache(self):
        with patch(f"{MODULE}.cache") as cache:
            self.run_command("reset_cache")
        cache.clear.assert_called_once()

    def test_reset_cache_error(self):
        with patch(f"{MODULE}.cache") as cache:
            cache.clear.side_effect = Exception("redis down")
            with self.assertRaisesRegex(CommandError, "Could not clear the cache: redis down"):
                self.run_command("reset_cache")
