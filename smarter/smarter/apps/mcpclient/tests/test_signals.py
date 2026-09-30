"""
Test :mod:`smarter.apps.mcpclient.signals`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.dispatch import Signal

from smarter.apps.mcpclient import signals
from smarter.lib.unittest.base_classes import SmarterTestBase

SIGNALS_WITH_RECEIVERS = (
    "mcpclient_connected",
    "mcpclient_connection_failed",
    "mcpclient_tool_called",
    "mcpclient_tool_responded",
    "mcpclient_tool_failed",
    "mcpclient_resource_read",
)


class TestMCPClientSignals(SmarterTestBase):
    """Test that the signals are Django Signals, with receivers."""

    def test_signals(self):
        """Test that each signal is a Django Signal."""
        for name in SIGNALS_WITH_RECEIVERS + ("mcpclient_called",):
            self.assertIsInstance(getattr(signals, name), Signal, name)

    def test_receivers(self):
        """Test that each lifecycle signal has a receiver in smarter.apps.mcpclient.receivers."""
        for name in SIGNALS_WITH_RECEIVERS:
            self.assertTrue(getattr(signals, name).has_listeners(), name)
