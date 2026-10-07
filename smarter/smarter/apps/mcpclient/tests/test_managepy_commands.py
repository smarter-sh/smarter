"""Tests for manage.py add_builtin_mcpclients."""

import io
from unittest import mock

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.tests.factories import secret_factory
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.utils import MCPClientExamples, add_builtin_mcpclients
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)

REFRESH_PATCH = "smarter.apps.mcpclient.receivers.refresh_mcpclient"


class ManageCommandAddBuiltinMCPClientsTestCase(TestAccountMixin):
    """
    Tests for manage.py add_builtin_mcpclients, and the add_builtin_mcpclients() util.

    The MCPClients are applied for the test account's admin user. Saving an MCPClient
    queues a catalog refresh, which would contact the real MCP server, so the refresh
    task is patched for every test.
    """

    examples: MCPClientExamples

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.examples = MCPClientExamples()

    def setUp(self):
        super().setUp()
        refresh_patcher = mock.patch(REFRESH_PATCH)
        self.mock_refresh = refresh_patcher.start()
        self.addCleanup(refresh_patcher.stop)
        self.addCleanup(self.delete_mcpclients)

    def delete_mcpclients(self):
        MCPClient.objects.filter(user_profile=self.user_profile).delete()

    def mcpclient_names(self) -> set[str]:
        return set(MCPClient.objects.filter(user_profile=self.user_profile).values_list("name", flat=True))

    def secret_is_visible(self, name: str) -> bool:
        """The same Secret lookup as the MCPClient broker."""
        if Secret.objects.filter(name=name, user_profile=self.user_profile).exists():
            return True
        return (
            Secret.objects.filter(name=name)
            .with_read_permission_for(self.admin_user)  # type: ignore[attr-defined]
            .exists()
        )

    def expected_names(self) -> set[str]:
        """The MCPClients that should be applied: no credentials, or a Secret the user can read."""
        return {
            example.name
            for example in self.examples.mcpclients
            if example.name and (not example.credentials or self.secret_is_visible(example.credentials))
        }

    def add_builtin_mcpclients(self, *args):
        call_command("add_builtin_mcpclients", "--username", self.admin_user.username, *args, stdout=io.StringIO())

    def test_examples(self):
        """Every built-in manifest loads, and has a name."""
        self.assertGreater(self.examples.count(), 0)
        self.assertEqual(self.examples.count(), len(self.examples.mcpclients))
        for example in self.examples.mcpclients:
            self.assertTrue(example.name, f"{example.filename} has no metadata.name")
            self.assertIsInstance(example.to_json(), dict)
            self.assertTrue(example.to_yaml())

    def test_example_credentials(self):
        """Credentials is the Secret name in spec.config.credentials, or None."""
        by_name = {example.name: example for example in self.examples.mcpclients}
        self.assertIsNone(by_name["deepwiki"].credentials)
        self.assertEqual(by_name["github"].credentials, "github_personal_access_token")

    def test_add_builtin_mcpclients(self):
        """The MCPClients without credentials are applied, and the others are skipped."""
        self.add_builtin_mcpclients()

        names = self.mcpclient_names()
        self.assertEqual(names, self.expected_names())
        for example in self.examples.mcpclients:
            if not example.credentials:
                self.assertIn(example.name, names)
        self.assertTrue(self.mock_refresh.delay.called)

    def test_add_builtin_mcpclients_verbose(self):
        """--verbose applies the same MCPClients."""
        self.add_builtin_mcpclients("--verbose")
        self.assertEqual(self.mcpclient_names(), self.expected_names())

    def test_add_builtin_mcpclients_is_idempotent(self):
        """Running the command again updates the MCPClients, and does not duplicate them."""
        self.add_builtin_mcpclients()
        count = MCPClient.objects.filter(user_profile=self.user_profile).count()

        self.add_builtin_mcpclients()
        self.assertEqual(MCPClient.objects.filter(user_profile=self.user_profile).count(), count)
        self.assertEqual(self.mcpclient_names(), self.expected_names())

    def test_add_builtin_mcpclients_after_secret_is_created(self):
        """A skipped MCPClient is applied once its Secret exists."""
        secret = secret_factory(
            user_profile=self.user_profile, name="github_personal_access_token", value="test-github-token"
        )
        self.addCleanup(secret.delete)

        self.add_builtin_mcpclients()

        github = MCPClient.objects.get(user_profile=self.user_profile, name="github")
        self.assertEqual(github.credentials, secret)

    def test_add_builtin_mcpclients_unknown_user(self):
        """An unknown username fails the command."""
        with self.assertRaises(SystemExit):
            call_command("add_builtin_mcpclients", "--username", "no_such_user_for_this_test", stdout=io.StringIO())
        self.assertEqual(self.mcpclient_names(), set())

    def test_add_builtin_mcpclients_util_requires_user_profile(self):
        """Add_builtin_mcpclients() requires a UserProfile."""
        with self.assertRaises(SmarterValueError):
            add_builtin_mcpclients(user_profile=None)
