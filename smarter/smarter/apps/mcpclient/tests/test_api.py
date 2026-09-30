"""
Test the MCPClient api, :mod:`smarter.apps.mcpclient.api.v1.views.views`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus
from unittest import mock

from django.urls import reverse
from rest_framework.test import APIClient

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.mcpclient.api.v1.urls import MCPClientApiV1ReverseViews as Names
from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.exceptions import SmarterMCPClientConnectionError
from smarter.apps.mcpclient.models import MCPClient, MCPConnectionStatus
from smarter.lib import json

from .base_classes import (
    MCPCLIENT_NAME,
    TEST_SERVER_NAME,
    MCPClientTestBase,
    mock_mcp_server,
)


def url(name: str, **kwargs) -> str:
    """Return the url of an MCPClient api view."""
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs)


class TestMCPClientApi(MCPClientTestBase):
    """Test the MCPClient api views, and their permissions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_admin_user, cls.other_account, cls.other_user_profile = admin_user_factory()
        cls.other_mcpclient = cls.create_mcpclient("test_mcpclient_other_account", user_profile=cls.other_user_profile)

    @classmethod
    def tearDownClass(cls):
        MCPClient.objects.filter(user_profile=cls.other_user_profile).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def get(self, path: str, status: int = HTTPStatus.OK) -> dict:
        """GET a path, assert the status, and return the json."""
        response = self.client.get(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content) if response.content else {}

    def post(self, path: str, data=None, status: int = HTTPStatus.OK) -> dict:
        """POST json to a path, assert the status, and return the json."""
        response = self.client.post(path, data=data or {}, format="json")
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content) if response.content else {}

    # -------------------------------------------------------------------------
    # list and detail
    # -------------------------------------------------------------------------
    def test_list(self):
        """Test that the list includes the account's MCPClients, and not another account's."""
        self.client.force_login(self.non_admin_user)
        data = self.get(url(Names.list_view))
        items = data["results"] if isinstance(data, dict) and "results" in data else data
        names = [item["name"] for item in items]
        self.assertIn(MCPCLIENT_NAME, names)
        self.assertNotIn(self.other_mcpclient.name, names)

    def test_detail(self):
        """Test the detail view, by hashed id and by id."""
        data = self.get(url(Names.mcpclient_by_hashed_id, hashed_id=self.mcpclient.hashed_id))
        self.assertEqual(data["name"], MCPCLIENT_NAME)
        data = self.get(url(Names.mcpclient_by_id, mcpclient_id=self.mcpclient.pk))
        self.assertEqual(data["name"], MCPCLIENT_NAME)

    def test_detail_other_account(self):
        """Test that another account's MCPClient is not found, for a user who is not a superuser."""
        self.client.force_login(self.non_admin_user)
        self.get(url(Names.mcpclient_by_id, mcpclient_id=self.other_mcpclient.pk), status=HTTPStatus.NOT_FOUND)

    def test_detail_shared(self):
        """Test that a user may read, but not delete, an MCPClient that is shared with them."""
        self.client.force_login(self.non_admin_user)
        self.get(url(Names.mcpclient_by_id, mcpclient_id=self.mcpclient.pk))
        response = self.client.delete(url(Names.mcpclient_by_id, mcpclient_id=self.mcpclient.pk))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTrue(MCPClient.objects.filter(pk=self.mcpclient.pk).exists())

    def test_delete(self):
        """Test that the owner may delete their MCPClient."""
        mcpclient = self.new_mcpclient("test_mcpclient_api_delete")
        response = self.client.delete(url(Names.mcpclient_by_id, mcpclient_id=mcpclient.pk))
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(MCPClient.objects.filter(pk=mcpclient.pk).exists())

    def test_anonymous(self):
        """Test that an anonymous user is refused."""
        self.client.logout()
        response = self.client.get(url(Names.list_view))
        self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))

    # -------------------------------------------------------------------------
    # MCP server
    # -------------------------------------------------------------------------
    def test_tools(self):
        """Test that the tools view returns the allowed tools, and the status."""
        with mock_mcp_server():
            data = self.get(url(Names.tools_by_hashed_id, hashed_id=self.mcpclient.hashed_id))
        self.assertEqual(sorted(tool["name"] for tool in data["tools"]), ["add_numbers", "echo", "fail"])
        self.assertEqual(data["serverName"], TEST_SERVER_NAME)
        self.assertEqual(data["status"], MCPConnectionStatus.CONNECTED)

    def test_tools_unreachable(self):
        """Test that an unreachable server is reported as a bad gateway."""
        with mock.patch.object(
            MCPServerConnection, "discover", side_effect=SmarterMCPClientConnectionError("server is down")
        ):
            data = self.get(url(Names.tools_by_id, mcpclient_id=self.mcpclient.pk), status=HTTPStatus.BAD_GATEWAY)
        self.assertIn("server is down", data["error"])
        self.assertEqual(data["status"], MCPConnectionStatus.ERROR)

    def test_refresh(self):
        """Test that the refresh view reconnects, and returns the status."""
        with mock_mcp_server() as guard:
            self.get(url(Names.tools_by_id, mcpclient_id=self.mcpclient.pk))
            data = self.post(url(Names.refresh_by_id, mcpclient_id=self.mcpclient.pk))
        self.assertEqual(guard.call_count, 2)
        self.assertEqual(data["status"], MCPConnectionStatus.CONNECTED)

    def test_refresh_requires_ownership(self):
        """Test that only the owner may refresh an MCPClient."""
        self.client.force_login(self.non_admin_user)
        self.post(url(Names.refresh_by_id, mcpclient_id=self.mcpclient.pk), status=HTTPStatus.NOT_FOUND)

    def test_tool_call(self):
        """Test that the owner may call a tool."""
        with mock_mcp_server():
            data = self.post(
                url(Names.tool_call_by_hashed_id, hashed_id=self.mcpclient.hashed_id, tool_name="add_numbers"),
                data={"a": 1, "b": 2},
            )
        self.assertEqual(data["content"], "3")
        self.assertFalse(data["isError"])

    def test_tool_call_not_allowed(self):
        """Test that a tool that allowedTools does not allow is forbidden."""
        with mock_mcp_server():
            self.post(
                url(Names.tool_call_by_id, mcpclient_id=self.mcpclient.pk, tool_name="secret_admin_tool"),
                status=HTTPStatus.FORBIDDEN,
            )

    def test_tool_call_requires_ownership(self):
        """Test that only the owner may call a tool."""
        self.client.force_login(self.non_admin_user)
        with mock_mcp_server():
            self.post(
                url(Names.tool_call_by_id, mcpclient_id=self.mcpclient.pk, tool_name="echo"),
                data={"text": "hi"},
                status=HTTPStatus.NOT_FOUND,
            )
