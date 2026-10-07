"""
Test :mod:`smarter.apps.mcpclient.caching`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from smarter.apps.mcpclient.caching import (
    catalog_cache_key,
    get_cached_catalog,
    get_cached_mcpclients_available_to_user_profile,
    get_cached_mcpclients_owned_by_user_profile,
    get_cached_mcpclients_shared_with_user_profile,
    invalidate_all_cached_mcpclients_for_user_profile,
    invalidate_cached_catalog,
)
from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.exceptions import SmarterMCPClientConnectionError
from smarter.apps.mcpclient.models import MCPClient, MCPConnectionStatus
from smarter.apps.mcpclient.signals import (
    mcpclient_connected,
    mcpclient_connection_failed,
)
from smarter.apps.plugin.plugin.tests.base_classes import capture_signal

from .base_classes import (
    GUARD_PATCH,
    MCPCLIENT_NAME,
    TEST_SERVER_NAME,
    TEST_SERVER_VERSION,
    MCPClientTestBase,
    mock_mcp_server,
)


class TestMCPClientCaching(MCPClientTestBase):
    """Test the cached MCPClient querysets, and the cached MCP server catalogs."""

    def names(self, qs) -> list[str]:
        """Return the names of the MCPClients in a queryset."""
        return [mcpclient.name for mcpclient in qs]

    # -------------------------------------------------------------------------
    # querysets
    # -------------------------------------------------------------------------
    def test_querysets(self):
        """Test that the admin user's MCPClients are owned by them, and shared with the account's non-admin user."""
        invalidate_all_cached_mcpclients_for_user_profile(self.user_profile)
        invalidate_all_cached_mcpclients_for_user_profile(self.non_admin_user_profile)
        self.assertIn(MCPCLIENT_NAME, self.names(get_cached_mcpclients_owned_by_user_profile(self.user_profile)))
        self.assertIn(MCPCLIENT_NAME, self.names(get_cached_mcpclients_available_to_user_profile(self.user_profile)))
        self.assertNotIn(
            MCPCLIENT_NAME, self.names(get_cached_mcpclients_owned_by_user_profile(self.non_admin_user_profile))
        )
        self.assertIn(
            MCPCLIENT_NAME, self.names(get_cached_mcpclients_shared_with_user_profile(self.non_admin_user_profile))
        )

    def test_querysets_invalidation(self):
        """Test that invalidation makes a new MCPClient visible."""
        get_cached_mcpclients_owned_by_user_profile(self.user_profile)
        self.new_mcpclient("test_mcpclient_caching_new")
        invalidate_all_cached_mcpclients_for_user_profile(self.user_profile)
        self.assertIn(
            "test_mcpclient_caching_new", self.names(get_cached_mcpclients_owned_by_user_profile(self.user_profile))
        )

    # -------------------------------------------------------------------------
    # catalogs
    # -------------------------------------------------------------------------
    def test_catalog_records_status(self):
        """Test that fetching a catalog records the connection in the MCPClient's status fields."""
        with mock_mcp_server(), capture_signal(mcpclient_connected) as connected:
            catalog = get_cached_catalog(self.mcpclient)
        self.assertEqual(catalog.server_name, TEST_SERVER_NAME)
        self.assertEqual(len(connected), 1)
        mcpclient = MCPClient.objects.get(pk=self.mcpclient.pk)
        self.assertEqual(mcpclient.status, MCPConnectionStatus.CONNECTED)
        self.assertEqual(mcpclient.server_name, TEST_SERVER_NAME)
        self.assertEqual(mcpclient.server_version, TEST_SERVER_VERSION)
        self.assertTrue(mcpclient.protocol_version)
        self.assertIsNotNone(mcpclient.last_connected_at)
        self.assertIsNone(mcpclient.last_error)
        # only the allowed tools are recorded
        self.assertEqual(sorted(mcpclient.tools), ["add_numbers", "echo", "fail"])
        # recording the status does not change updated_at, so it is not a configuration change
        self.assertEqual(mcpclient.updated_at, self.mcpclient.updated_at)

    def test_catalog_is_cached(self):
        """Test that the catalog is cached, so that the server is not contacted again."""
        with mock_mcp_server():
            get_cached_catalog(self.mcpclient)
        with mock.patch.object(MCPServerConnection, "discover") as discover:
            catalog = get_cached_catalog(self.mcpclient)
        discover.assert_not_called()
        self.assertEqual(catalog.server_name, TEST_SERVER_NAME)

    def test_catalog_refresh(self):
        """Test that refresh bypasses the cache."""
        with mock_mcp_server():
            get_cached_catalog(self.mcpclient)
            with mock.patch.object(MCPServerConnection, "discover", wraps=MCPServerConnection(self.mcpclient).discover):
                get_cached_catalog(self.mcpclient, refresh=True)

    def test_catalog_not_cached_when_ttl_is_zero(self):
        """Test that a cacheTtl of 0 disables caching."""
        mcpclient = self.new_mcpclient("test_mcpclient_no_cache", cache_ttl=0)
        with mock_mcp_server() as guard:
            get_cached_catalog(mcpclient)
            get_cached_catalog(mcpclient)
        self.assertEqual(guard.call_count, 2)

    def test_fingerprint_changes_cache_key(self):
        """Test that changing how the MCPClient connects changes its cache key, while its status does not."""
        key = catalog_cache_key(self.mcpclient)
        mcpclient = MCPClient.objects.get(pk=self.mcpclient.pk)
        mcpclient.status = MCPConnectionStatus.ERROR
        mcpclient.last_error = "an error"
        self.assertEqual(catalog_cache_key(mcpclient), key)
        mcpclient.allowed_tools = ["echo"]
        self.assertNotEqual(catalog_cache_key(mcpclient), key)
        mcpclient.allowed_tools = self.mcpclient.allowed_tools
        mcpclient.endpoint_url = "https://mcp.example.org/mcp"
        self.assertNotEqual(catalog_cache_key(mcpclient), key)

    def test_failure_is_recorded_and_cached(self):
        """Test that a failed connection is recorded, and remembered, so that prompts do not wait on it."""
        with (
            mock.patch(GUARD_PATCH),
            mock.patch.object(
                MCPServerConnection, "discover", side_effect=SmarterMCPClientConnectionError("server is down")
            ) as discover,
            capture_signal(mcpclient_connection_failed) as failed,
        ):
            with self.assertRaises(SmarterMCPClientConnectionError):
                get_cached_catalog(self.mcpclient)
            with self.assertRaises(SmarterMCPClientConnectionError):
                get_cached_catalog(self.mcpclient)
        self.assertEqual(discover.call_count, 1)
        self.assertEqual(len(failed), 1)
        mcpclient = MCPClient.objects.get(pk=self.mcpclient.pk)
        self.assertEqual(mcpclient.status, MCPConnectionStatus.ERROR)
        self.assertIn("server is down", mcpclient.last_error)

    def test_invalidate_clears_failure(self):
        """Test that invalidating the catalog also forgets a cached failure."""
        with mock.patch.object(
            MCPServerConnection, "discover", side_effect=SmarterMCPClientConnectionError("server is down")
        ):
            with self.assertRaises(SmarterMCPClientConnectionError):
                get_cached_catalog(self.mcpclient)
        invalidate_cached_catalog(self.mcpclient)
        with mock_mcp_server():
            self.assertEqual(get_cached_catalog(self.mcpclient).server_name, TEST_SERVER_NAME)
        self.mcpclient.refresh_from_db()
        self.assertEqual(self.mcpclient.status, MCPConnectionStatus.CONNECTED)
        self.assertIsNone(self.mcpclient.last_error)
