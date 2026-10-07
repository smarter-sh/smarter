"""
Test :mod:`smarter.apps.mcpclient.tasks`.

The Celery tasks are called directly, which runs them synchronously, in this process.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.exceptions import SmarterMCPClientConnectionError
from smarter.apps.mcpclient.models import MCPClient, MCPConnectionStatus
from smarter.apps.mcpclient.tasks import refresh_mcpclient, refresh_mcpclients

from .base_classes import TEST_SERVER_NAME, MCPClientTestBase, mock_mcp_server


class TestMCPClientTasks(MCPClientTestBase):
    """Test refresh_mcpclient() and refresh_mcpclients()."""

    def test_refresh_mcpclient(self):
        """Test that refresh_mcpclient() connects, and records the connection."""
        with mock_mcp_server():
            status = refresh_mcpclient(self.mcpclient.pk)
        self.assertEqual(status, MCPConnectionStatus.CONNECTED)
        mcpclient = MCPClient.objects.get(pk=self.mcpclient.pk)
        self.assertEqual(mcpclient.server_name, TEST_SERVER_NAME)
        self.assertEqual(sorted(mcpclient.tools), ["add_numbers", "echo", "fail"])

    def test_refresh_mcpclient_bypasses_the_cache(self):
        """Test that refresh_mcpclient() reconnects even if the catalog is cached."""
        with mock_mcp_server() as guard:
            refresh_mcpclient(self.mcpclient.pk)
            refresh_mcpclient(self.mcpclient.pk)
        self.assertEqual(guard.call_count, 2)

    def test_refresh_mcpclient_failure(self):
        """Test that an unreachable server is recorded, and does not fail the task."""
        with mock.patch.object(
            MCPServerConnection, "discover", side_effect=SmarterMCPClientConnectionError("server is down")
        ):
            status = refresh_mcpclient(self.mcpclient.pk)
        self.assertEqual(status, MCPConnectionStatus.ERROR)
        self.assertIn("server is down", MCPClient.objects.get(pk=self.mcpclient.pk).last_error)

    def test_refresh_mcpclient_missing(self):
        """Test that refresh_mcpclient() does nothing for an MCPClient that does not exist."""
        self.assertIsNone(refresh_mcpclient(999999999))

    def test_refresh_mcpclients(self):
        """Test that refresh_mcpclients() queues a refresh of every active MCPClient."""
        inactive = self.new_mcpclient("test_mcpclient_tasks_inactive", is_active=False)
        with mock.patch("smarter.apps.mcpclient.tasks.refresh_mcpclient") as task:
            count = refresh_mcpclients()
        queued = [call.args[0] for call in task.delay.call_args_list]
        self.assertEqual(count, len(queued))
        self.assertIn(self.mcpclient.pk, queued)
        self.assertNotIn(inactive.pk, queued)
