"""
Test :mod:`smarter.apps.mcpclient.receivers`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from django.core.cache import cache

from smarter.apps.mcpclient import receivers
from smarter.apps.mcpclient.caching import catalog_cache_key
from smarter.apps.mcpclient.connection import MCPServerCatalog
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.signals import (
    mcpclient_connected,
    mcpclient_connection_failed,
    mcpclient_resource_read,
    mcpclient_tool_called,
    mcpclient_tool_failed,
    mcpclient_tool_responded,
)

from .base_classes import MCPClientTestBase

REFRESH_PATCH = "smarter.apps.mcpclient.receivers.refresh_mcpclient"


class TestMCPClientReceivers(MCPClientTestBase):
    """Test the mcpclient app's model and signal receivers."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(receivers, "logger")
        self.logger = patcher.start()
        self.addCleanup(patcher.stop)
        self.messages: list[str] = []
        self.logger.info.side_effect = self.log
        self.logger.warning.side_effect = self.log

    def log(self, msg, *args, **kwargs):  # pylint: disable=W0613
        """Record a formatted log message."""
        self.messages.append(msg % args if args else msg)

    def logged(self) -> str:
        """Return everything the receivers logged, as one string."""
        return "\n".join(self.messages)

    def test_saved_queues_refresh(self):
        """Test that saving an active MCPClient queues a refresh of its catalog."""
        with mock.patch(REFRESH_PATCH) as refresh:
            mcpclient = MCPClient.objects.create(
                name="test_mcpclient_receivers_saved",
                user_profile=self.user_profile,
                endpoint_url="https://mcp.example.com/mcp",
            )
            self.addCleanup(MCPClient.objects.filter(pk=mcpclient.pk).delete)
            mcpclient.description = "updated"
            mcpclient.save()
        self.assertEqual(refresh.delay.call_count, 2)
        refresh.delay.assert_called_with(mcpclient.pk)
        self.assertIn("created", self.logged())
        self.assertIn("updated", self.logged())

    def test_saved_inactive_does_not_refresh(self):
        """Test that saving an inactive MCPClient does not queue a refresh."""
        with mock.patch(REFRESH_PATCH) as refresh:
            self.new_mcpclient("test_mcpclient_receivers_inactive", is_active=False)
        refresh.delay.assert_not_called()

    def test_deleted_invalidates_catalog(self):
        """Test that deleting an MCPClient invalidates its cached catalog."""
        mcpclient = self.new_mcpclient("test_mcpclient_receivers_deleted")
        key = catalog_cache_key(mcpclient)
        cache.set(key, {"tools": []}, 60)
        mcpclient.delete()
        self.assertIsNone(cache.get(key))
        self.assertIn("mcpclient_deleted", self.logged())

    def test_signal_receivers(self):
        """Test that each signal's receiver logs it."""
        catalog = MCPServerCatalog(server_name="test-server", server_version="1", protocol_version="2025-11-25")
        mcpclient_connected.send(sender=self.__class__, mcpclient=self.mcpclient, catalog=catalog)
        mcpclient_connection_failed.send(sender=self.__class__, mcpclient=self.mcpclient, error="refused")
        mcpclient_tool_called.send(
            sender=self.__class__, mcpclient=self.mcpclient, tool_name="echo", arguments={"text": "private"}
        )
        mcpclient_tool_responded.send(
            sender=self.__class__, mcpclient=self.mcpclient, tool_name="echo", is_error=False, characters=7
        )
        mcpclient_tool_failed.send(sender=self.__class__, mcpclient=self.mcpclient, tool_name="echo", error="HTTP 500")
        mcpclient_resource_read.send(
            sender=self.__class__, mcpclient=self.mcpclient, uri="docs://test/readme", characters=3
        )
        logged = self.logged()
        for text in ("test-server", "refused", "echo", "characters: 7", "HTTP 500", "docs://test/readme"):
            self.assertIn(text, logged)
        # tool arguments may contain user data, and are not logged
        self.assertNotIn("private", logged)
