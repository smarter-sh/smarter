"""Test the reset_cache management command."""

from unittest.mock import patch

from smarter.apps.account.management.commands.reset_cache import Command

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.reset_cache"


class TestResetCache(CommandTestBase):
    """The cache is patched, so that the command doesn't clear the cache that other tests share."""

    def test_reset_cache(self):
        with patch(f"{MODULE}.cache") as cache:
            self.run_command("reset_cache")
        cache.clear.assert_called_once()

    def test_reset_cache_error(self):
        with patch(f"{MODULE}.cache") as cache, patch.object(Command, "handle_completed_failure") as failure:
            cache.clear.side_effect = Exception("redis down")
            self.run_command("reset_cache")
        failure.assert_called_once()
