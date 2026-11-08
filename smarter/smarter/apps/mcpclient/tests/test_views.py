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

from smarter.apps.mcpclient.api.web.urls import MCPClientApiWebReverseNames as WebNames
from smarter.apps.mcpclient.caching import (
    invalidate_all_cached_mcpclients_for_user_profile,
)
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.urls import MCPClientReverseNames as Names
from smarter.lib import json
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.resource_views import (
    ResourceViewsTestMixin,
    assert_console_page,
    assert_no_resource,
    resource_detail_json,
)

from .base_classes import MCPCLIENT_NAME, MCPClientTestBase


def url(name: str, **kwargs) -> str:
    """Return the url of an MCPClient dashboard view."""
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs or None)


def web_url(name: str, **kwargs) -> str:
    """Return the url of an MCPClient endpoint in the web console's api."""
    return reverse(f"{WebNames.namespace}:{name}", kwargs=kwargs or None)


class TestMCPClientViews(MCPClientTestBase):
    """Test the MCPClient dashboard views."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)
        invalidate_all_cached_mcpclients_for_user_profile(self.user_profile)

    def post(self, path: str, status: int = HTTPStatus.OK) -> SmarterDictType:
        """POST to a path, assert the status, and return the json."""
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def test_listview(self):
        """Test the React list page."""
        response = self.client.get(url(Names.listview))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_listview_anonymous(self):
        """Test that the list page is the single-page console's, which sends an anonymous user to sign in."""
        assert_console_page(self, url(Names.listview))

    def test_web_api_paths(self):
        """Test that the list page's endpoints are in the web console's api."""
        self.assertEqual(web_url(WebNames.listview_all), "/api/web/mcpclient/listview/")
        self.assertEqual(web_url(WebNames.listview, ownership_filter="owned"), "/api/web/mcpclient/listview/owned/")
        self.assertEqual(web_url(WebNames.clone, mcpclient_id=1, new_name="x"), "/api/web/mcpclient/clone/1/x/")
        self.assertEqual(web_url(WebNames.rename, mcpclient_id=1, new_name="x"), "/api/web/mcpclient/rename/1/x/")
        self.assertEqual(web_url(WebNames.delete, mcpclient_id=1), "/api/web/mcpclient/delete/1/")

    def test_listview_api(self):
        """Test that the list api returns the user's MCPClients."""
        data = self.post(web_url(WebNames.listview_all))
        self.assertIn(MCPCLIENT_NAME, [item["name"] for item in data["objects"]])

    def test_clone(self):
        """Test that the clone api clones an MCPClient."""
        clone_name = "test_mcpclient_clone"
        self.addCleanup(MCPClient.objects.filter(name=clone_name).delete)
        data = self.post(web_url(WebNames.clone, mcpclient_id=self.mcpclient.pk, new_name=clone_name))
        self.assertEqual(data["name"], clone_name)
        clone = MCPClient.objects.get(name=clone_name, user_profile=self.user_profile)
        self.assertEqual(clone.endpoint_url, self.mcpclient.endpoint_url)
        self.assertEqual(clone.allowed_tools, self.mcpclient.allowed_tools)

    def test_rename(self):
        """Test that the rename api renames an MCPClient."""
        mcpclient = self.new_mcpclient("test_mcpclient_rename")
        data = self.post(web_url(WebNames.rename, mcpclient_id=mcpclient.pk, new_name="test_mcpclient_renamed"))
        self.assertEqual(data["name"], "test_mcpclient_renamed")

    def test_delete(self):
        """Test that the delete api deletes an MCPClient."""
        mcpclient = self.new_mcpclient("test_mcpclient_view_delete")
        self.post(web_url(WebNames.delete, mcpclient_id=mcpclient.pk))
        self.assertFalse(MCPClient.objects.filter(pk=mcpclient.pk).exists())

    def test_delete_not_owner(self):
        """Test that a user cannot delete an MCPClient that is only shared with them."""
        self.client.force_login(self.non_admin_user)
        self.post(web_url(WebNames.delete, mcpclient_id=self.mcpclient.pk), status=HTTPStatus.NOT_FOUND)
        self.assertTrue(MCPClient.objects.filter(pk=self.mcpclient.pk).exists())

    def test_detailview(self):
        """Test that the manifest page is the console's, whose resource api returns the MCPClient's manifest."""
        detail = resource_detail_json(self, self.mcpclient.record_locator)
        self.assertEqual(detail["kind"], "MCPClient")
        self.assertEqual(detail["name"], MCPCLIENT_NAME)
        self.assertIn(MCPCLIENT_NAME, detail["manifest"] or "")
        self.assertIn("mcp.example.com", detail["manifest"] or "")
        assert_console_page(self, url(Names.detailview, hashed_id=self.mcpclient.hashed_id))

    def test_detailview_invalid(self):
        """Test that the resource api has no MCPClient for an invalid identifier."""
        assert_no_resource(self, "mcpclient-not-a-hash")

    def test_detailview_unknown_id(self):
        """Test that the resource api has no MCPClient for a valid hashed id of one that doesn't exist."""
        assert_no_resource(self, MCPClient(id=999999999).record_locator)


class TestMCPClientResourceViews(ResourceViewsTestMixin, MCPClientTestBase):
    """Test the MCPClient list page, list, clone, delete and rename apis, and detail page with the shared mixin."""

    model = MCPClient
    reverse_names = Names
    web_reverse_names = WebNames
    id_kwarg = "mcpclient_id"
    invalidate_cache = staticmethod(invalidate_all_cached_mcpclients_for_user_profile)
    resource_name_prefix = "test_mcpclient_resource_views"

    @classmethod
    def create_resource(cls, name: str) -> MCPClient:
        return cls.create_mcpclient(name)
