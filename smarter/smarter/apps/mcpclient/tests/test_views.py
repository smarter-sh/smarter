"""
Test the MCPClient dashboard views: the React list page, its api, and the manifest detail page.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.mcpclient.caching import (
    invalidate_all_cached_mcpclients_for_user_profile,
)
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.urls import MCPClientReverseNames as Names
from smarter.lib import json

from .base_classes import MCPCLIENT_NAME, MCPClientTestBase


def url(name: str, **kwargs) -> str:
    """Return the url of an MCPClient dashboard view."""
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs or None)


class TestMCPClientViews(MCPClientTestBase):
    """Test the MCPClient dashboard views."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)
        invalidate_all_cached_mcpclients_for_user_profile(self.user_profile)

    def post(self, path: str, status: int = HTTPStatus.OK) -> dict:
        """POST to a path, assert the status, and return the json."""
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def test_listview(self):
        """Test the React list page."""
        response = self.client.get(url(Names.listview))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_listview_anonymous(self):
        """Test that an anonymous user is redirected to the login page."""
        self.client.logout()
        response = self.client.get(url(Names.listview))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_listview_api(self):
        """Test that the list api returns the user's MCPClients."""
        data = self.post(url(Names.listview_api_all))
        self.assertIn(MCPCLIENT_NAME, [item["name"] for item in data["objects"]])

    def test_clone(self):
        """Test that the clone api clones an MCPClient."""
        clone_name = "test_mcpclient_clone"
        self.addCleanup(MCPClient.objects.filter(name=clone_name).delete)
        data = self.post(url(Names.listview_api_clone, mcpclient_id=self.mcpclient.pk, new_name=clone_name))
        self.assertEqual(data["name"], clone_name)
        clone = MCPClient.objects.get(name=clone_name, user_profile=self.user_profile)
        self.assertEqual(clone.endpoint_url, self.mcpclient.endpoint_url)
        self.assertEqual(clone.allowed_tools, self.mcpclient.allowed_tools)

    def test_rename(self):
        """Test that the rename api renames an MCPClient."""
        mcpclient = self.new_mcpclient("test_mcpclient_rename")
        data = self.post(url(Names.listview_api_rename, mcpclient_id=mcpclient.pk, new_name="test_mcpclient_renamed"))
        self.assertEqual(data["name"], "test_mcpclient_renamed")

    def test_delete(self):
        """Test that the delete api deletes an MCPClient."""
        mcpclient = self.new_mcpclient("test_mcpclient_view_delete")
        self.post(url(Names.listview_api_delete, mcpclient_id=mcpclient.pk))
        self.assertFalse(MCPClient.objects.filter(pk=mcpclient.pk).exists())

    def test_delete_not_owner(self):
        """Test that a user cannot delete an MCPClient that is only shared with them."""
        self.client.force_login(self.non_admin_user)
        self.post(url(Names.listview_api_delete, mcpclient_id=self.mcpclient.pk), status=HTTPStatus.NOT_FOUND)
        self.assertTrue(MCPClient.objects.filter(pk=self.mcpclient.pk).exists())

    def test_detailview(self):
        """Test that the detail page renders the MCPClient's manifest."""
        response = self.client.get(url(Names.detailview, hashed_id=self.mcpclient.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode()
        self.assertIn(MCPCLIENT_NAME, content)
        self.assertIn("mcp.example.com", content)

    def test_detailview_invalid(self):
        """Test that an invalid identifier is not found."""
        response = self.client.get(url(Names.detailview, hashed_id="not-a-hash"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
