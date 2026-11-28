"""Test manage.py initialize_llmtool_api_keys: :mod:`smarter.apps.llmtool.management.commands.initialize_llmtool_api_keys`."""

from io import StringIO
from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmtool.management.commands import initialize_llmtool_api_keys
from smarter.apps.llmtool.management.commands.initialize_llmtool_api_keys import (
    Command,
)
from smarter.apps.secret.models import Secret


class TestInitializeLLMToolApiKeys(TestAccountMixin):
    """The command reports which llmtool api key Secrets don't exist; it never reads an environment variable."""

    def setUp(self):
        super().setUp()
        self.command = Command(stdout=StringIO(), stderr=StringIO())
        # the test account's user stands in for the Smarter admin, whose Secrets the command checks.
        patcher = patch.object(
            initialize_llmtool_api_keys,
            "smarter_cached_objects",
            MagicMock(smarter_admin_user_profile=self.user_profile),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def admin_secret(self, name: str) -> None:
        """Create one of the test admin's Secrets, deleted when the test ends."""
        secret = Secret.objects.create(name=name, user_profile=self.user_profile, encrypted_value=Secret.encrypt("k"))
        self.addCleanup(Secret.objects.filter(pk=secret.pk).delete)

    def test_both_secrets_exist(self):
        """The Tavily and Brave Search Secrets keep their names, which the plugins' manifests name."""
        self.admin_secret("tavily_api_key")
        self.admin_secret("brave_search_api_key")
        with patch.object(initialize_llmtool_api_keys.logger, "error") as error:
            self.command.handle()
        error.assert_not_called()

    def test_a_missing_secret_is_reported(self):
        """The banner names the missing Secret, and how to set it, never an environment variable."""
        self.admin_secret("brave_search_api_key")
        with (
            patch.dict("os.environ", {"SMARTER_APP_LLMTOOL_TAVILY_API_KEY": "tavily-key"}),
            patch.object(initialize_llmtool_api_keys.logger, "error") as error,
        ):
            self.command.handle()
        banner = error.call_args.args[0]
        self.assertIn("tavily_api_key", banner)
        self.assertIn("bootstrap", banner)
        self.assertNotIn("brave_search_api_key", banner)
        self.assertNotIn("SMARTER_APP_LLMTOOL", banner)
        # the variable is ignored: the key's only source is its Secret.
        self.assertFalse(Secret.objects.filter(name="tavily_api_key", user_profile=self.user_profile).exists())
