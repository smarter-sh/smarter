"""
Test :mod:`smarter.apps.mcpclient.admin`, and the LLMClientMCPClients admin.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.llmclient.admin import LLMClientMCPClientsAdmin
from smarter.apps.llmclient.models import LLMClient, LLMClientMCPClients
from smarter.apps.mcpclient.admin import MCPClientAdmin
from smarter.apps.mcpclient.models import MCPClient

from .base_classes import MCPCLIENT_NAME, MCPClientTestBase


class TestMCPClientAdmin(MCPClientTestBase):
    """Test the MCPClient and LLMClientMCPClients ModelAdmins."""

    def request(self, user=None):
        """Return a GET request for the admin site, by ``user``, which defaults to the admin user."""
        request = RequestFactory().get("/admin/")
        request.user = user or self.admin_user
        return request

    def model_admin(self, model):
        """Return the ModelAdmin that is registered for ``model``."""
        return smarter_restricted_admin_site._registry[model]  # pylint: disable=W0212

    def test_registered(self):
        """Test that the ModelAdmins are registered."""
        self.assertIsInstance(self.model_admin(MCPClient), MCPClientAdmin)
        self.assertIsInstance(self.model_admin(LLMClientMCPClients), LLMClientMCPClientsAdmin)

    def test_queryset(self):
        """Test that the owner sees their MCPClients, and an anonymous user sees none."""
        model_admin = self.model_admin(MCPClient)
        self.assertIn(self.mcpclient, model_admin.get_queryset(self.request()))
        self.assertFalse(model_admin.get_queryset(self.request(AnonymousUser())).exists())

    def test_queryset_excludes_other_accounts(self):
        """Test that a user does not administer another account's MCPClients."""
        other = self.new_mcpclient("test_mcpclient_admin_other", user_profile=self.non_admin_user_profile)
        qs = self.model_admin(MCPClient).get_queryset(self.request(self.non_admin_user))
        self.assertIn(other, qs)
        self.assertNotIn(self.mcpclient, qs)

    def test_status_fields_are_read_only(self):
        """Test that the connection status fields are read only."""
        readonly = self.model_admin(MCPClient).get_readonly_fields(self.request())
        for field in ("status", "protocol_version", "server_name", "tools", "last_connected_at", "last_error"):
            self.assertIn(field, readonly)

    def test_llmclient_mcpclients_queryset(self):
        """Test that the LLMClientMCPClients admin lists the links of the user's LLMClients."""
        llmclient = LLMClient.objects.create(name="test_mcpclient_admin_llmclient", user_profile=self.user_profile)
        self.addCleanup(llmclient.delete)
        link = LLMClientMCPClients.objects.create(llmclient=llmclient, mcpclient=self.mcpclient)
        model_admin = self.model_admin(LLMClientMCPClients)
        self.assertIn(link, model_admin.get_queryset(self.request()))
        self.assertNotIn(link, model_admin.get_queryset(self.request(self.non_admin_user)))
        self.assertFalse(model_admin.get_queryset(self.request(AnonymousUser())).exists())

    def test_changelist(self):
        """Test that the admin user can open the MCPClient changelist."""
        client = Client()
        client.force_login(self.admin_user)
        self.addCleanup(client.logout)
        response = client.get("/admin/mcpclient/mcpclient/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(MCPCLIENT_NAME, response.content.decode())
