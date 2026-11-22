"""Test manage.py initialize_llmtool_api_keys: :mod:`smarter.apps.llmtool.management.commands.initialize_llmtool_api_keys`."""

import os
from io import StringIO
from unittest.mock import patch

from smarter.apps.llmtool.management.commands import initialize_llmtool_api_keys
from smarter.apps.llmtool.management.commands.initialize_llmtool_api_keys import (
    Command,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

VARIABLES = (
    "APP_LLMTOOL_TAVILY_API_KEY",
    "SMARTER_APP_LLMTOOL_TAVILY_API_KEY",
    "APP_LLMTOOL_BRAVE_SEARCH_API_KEY",
    "SMARTER_APP_LLMTOOL_BRAVE_SEARCH_API_KEY",
)


class TestInitializeLLMToolApiKeys(SmarterTestBase):
    """Each llmtool api key that is set is stored as its Secret; a missing one is reported, never stored."""

    def setUp(self):
        super().setUp()
        self.command = Command(stdout=StringIO(), stderr=StringIO())
        environ = patch.dict(os.environ, {})
        environ.start()
        self.addCleanup(environ.stop)
        for name in VARIABLES:
            os.environ.pop(name, None)
        for target in ("initialize_secret", "smarter_cached_objects"):
            patcher = patch.object(initialize_llmtool_api_keys, target)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def stored(self) -> dict[str, str]:
        """The Secrets that the command stored, by name, with their values."""
        return {
            call.kwargs["secret_name"]: call.kwargs["secret_string"]
            for call in self.initialize_secret.call_args_list  # type: ignore[attr-defined]
        }

    def test_both_keys(self):
        """The Tavily and Brave Search keys keep their Secrets' names, which the plugins' manifests name."""
        os.environ["APP_LLMTOOL_TAVILY_API_KEY"] = "tavily-key"
        os.environ["SMARTER_APP_LLMTOOL_BRAVE_SEARCH_API_KEY"] = "brave-key"
        with patch.object(initialize_llmtool_api_keys.logger, "error") as error:
            self.command.handle()
        self.assertEqual(self.stored(), {"tavily_api_key": "tavily-key", "brave_search_api_key": "brave-key"})
        error.assert_not_called()

    def test_a_missing_key_is_not_stored(self):
        """No key, a .env.example placeholder, or the Helm chart's, stores nothing, and the banner names the variable."""
        for value in (None, "SET-ME-PLEASE", "SET-ME-IN-helm/charts/smarter/values.yaml"):
            with self.subTest(value=value):
                self.initialize_secret.reset_mock()  # type: ignore[attr-defined]
                os.environ.pop("APP_LLMTOOL_TAVILY_API_KEY", None)
                if value:
                    os.environ["APP_LLMTOOL_TAVILY_API_KEY"] = value
                os.environ["APP_LLMTOOL_BRAVE_SEARCH_API_KEY"] = "brave-key"
                with patch.object(initialize_llmtool_api_keys.logger, "error") as error:
                    self.command.handle()
                self.assertEqual(self.stored(), {"brave_search_api_key": "brave-key"})
                banner = error.call_args.args[0]
                self.assertIn("SMARTER_APP_LLMTOOL_TAVILY_API_KEY", banner)
                self.assertIn("manage.py initialize_llmtool_api_keys", banner)
                self.assertNotIn("BRAVE", banner)
