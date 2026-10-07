"""
Test the seed_chat_history management command.

The command seeds the Smarter account's example llmclient, and sends each
seed prompt to the LLM. These tests point it at the test account instead,
and mock the LLM handler and the llmclient's plugins.
"""

import glob
import os
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient, LLMClientPlugin
from smarter.apps.prompt.management.commands import seed_chat_history
from smarter.apps.prompt.models import Prompt
from smarter.common.const import SMARTER_EXAMPLE_LLM_CLIENT_NAME

MODULE = "smarter.apps.prompt.management.commands.seed_chat_history"


class TestSeedChatHistory(TestAccountMixin):
    """Test manage.py seed_chat_history."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(name=SMARTER_EXAMPLE_LLM_CLIENT_NAME, user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.addCleanup(Prompt.objects.filter(llmclient=self.llmclient).delete)
        self.seed_files = glob.glob(os.path.join(seed_chat_history.HERE, "data", "*.json"))
        for patcher in (
            patch(f"{MODULE}.SMARTER_ACCOUNT_NUMBER", self.account.account_number),
            patch(f"{MODULE}.default_handler"),
            patch.object(LLMClientPlugin, "plugins", return_value=[MagicMock(name="plugin")]),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_command(self) -> str:
        out = StringIO()
        call_command("seed_chat_history", stdout=out, stderr=out)
        return out.getvalue()

    def test_seeds_every_prompt_file(self):
        self.assertTrue(self.seed_files)
        output = self.run_command()
        self.assertEqual(seed_chat_history.default_handler.call_count, len(self.seed_files))
        kwargs = seed_chat_history.default_handler.call_args.kwargs
        self.assertEqual(kwargs["prompt"].llmclient, self.llmclient)
        self.assertEqual(kwargs["prompt"].user_profile, self.user_profile)
        self.assertEqual(kwargs["user"], self.admin_user)
        self.assertIsInstance(kwargs["data"], dict)
        self.assertEqual(output.count("Prompt history seeded."), len(self.seed_files))
        self.assertEqual(Prompt.objects.filter(llmclient=self.llmclient).count(), 1)

    def test_requires_plugins(self):
        with patch.object(LLMClientPlugin, "plugins", return_value=[]):
            with self.assertRaises(ValueError):
                self.run_command()
        seed_chat_history.default_handler.assert_not_called()

    def test_requires_the_example_llmclient(self):
        LLMClient.objects.filter(pk=self.llmclient.pk).delete()
        with self.assertRaises(LLMClient.DoesNotExist):
            self.run_command()

    def test_requires_an_admin_user(self):
        with patch(f"{MODULE}.get_cached_admin_user_for_account", return_value=None):
            with self.assertRaises(ValueError):
                self.run_command()
        with patch.object(seed_chat_history.UserProfile, "get_cached_object", return_value=None):
            with self.assertRaises(ValueError):
                self.run_command()
        seed_chat_history.default_handler.assert_not_called()
