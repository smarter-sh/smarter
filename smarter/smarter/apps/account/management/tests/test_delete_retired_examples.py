"""Test the delete_retired_examples management command."""

from unittest import mock

from django.core.management.base import CommandError

from smarter.apps.account.management.commands.delete_retired_examples import (
    RETIRED_EXAMPLES,
    RetiredExample,
)
from smarter.apps.llmclient.models import LLMClient, LLMClientMCPClients
from smarter.apps.mcpclient.models import MCPClient

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.delete_retired_examples"


class TestDeleteRetiredExamples(CommandTestBase):
    """Test that the retired example resources of the Smarter admin are deleted, and nothing else."""

    def setUp(self):
        super().setUp()
        self.name = self.unique("retired_mcpclient")
        self.retired = (RetiredExample(model=MCPClient, name=self.name, reason="it was retired."),)
        self.patcher = mock.patch(f"{MODULE}.RETIRED_EXAMPLES", self.retired)
        self.patcher.start()
        self.created: list = []

    def tearDown(self):
        self.patcher.stop()
        for obj in reversed(self.created):
            if obj.pk and type(obj).objects.filter(pk=obj.pk).exists():
                obj.delete()
        super().tearDown()

    def mcpclient(self, user_profile) -> MCPClient:
        """Create an MCPClient of the retired name, without connecting to its MCP server."""
        with mock.patch("smarter.apps.mcpclient.receivers.refresh_mcpclient"):
            obj = MCPClient.objects.create(
                user_profile=user_profile,
                name=self.name,
                description="A retired example.",
                version="1.0.0",
                endpoint_url="https://mcp.example.com/mcp/",
            )
        self.created.append(obj)
        return obj

    def test_retired_examples_name_existing_models(self):
        """Test that each retired example is unique, and has a name and a reason."""
        keys = [(example.model, example.name) for example in RETIRED_EXAMPLES]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn((MCPClient, "smarter_project_github_chat"), keys)
        for example in RETIRED_EXAMPLES:
            self.assertTrue(example.name)
            self.assertTrue(example.reason)

    def test_deletes_the_owners_retired_example_and_its_links(self):
        mcpclient = self.mcpclient(self.user_profile)
        llmclient = LLMClient.objects.create(user_profile=self.user_profile, name=self.unique("llmclient"))
        self.created.append(llmclient)
        LLMClientMCPClients.objects.create(llmclient=llmclient, mcpclient=mcpclient)

        output = self.run_command("delete_retired_examples", username=self.admin_user.username)

        self.assertFalse(MCPClient.objects.filter(pk=mcpclient.pk).exists())
        self.assertFalse(LLMClientMCPClients.objects.filter(llmclient=llmclient).exists())
        self.assertTrue(LLMClient.objects.filter(pk=llmclient.pk).exists())
        self.assertIn(f"Deleted the retired example MCPClient {self.name}: it was retired.", output)
        self.assertIn("Deleted 1 of the 1 retired example resources.", output)

    def test_is_idempotent(self):
        self.mcpclient(self.user_profile)
        self.run_command("delete_retired_examples", username=self.admin_user.username)
        output = self.run_command("delete_retired_examples", username=self.admin_user.username)
        self.assertIn("Deleted 0 of the 1 retired example resources.", output)

    def test_keeps_another_users_resource_of_the_same_name(self):
        theirs = self.mcpclient(self.non_admin_user_profile)
        output = self.run_command("delete_retired_examples", username=self.admin_user.username)
        self.assertTrue(MCPClient.objects.filter(pk=theirs.pk).exists())
        self.assertIn("Deleted 0 of the 1 retired example resources.", output)

    def test_defaults_to_the_smarter_admin(self):
        mcpclient = self.mcpclient(self.user_profile)
        with mock.patch(f"{MODULE}.smarter_settings") as settings:
            settings.admin_username = self.admin_user.username
            self.run_command("delete_retired_examples")
        self.assertFalse(MCPClient.objects.filter(pk=mcpclient.pk).exists())

    def test_unknown_user_fails(self):
        with self.assertRaises(CommandError):
            self.run_command("delete_retired_examples", username=self.unique("nobody"))
