# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.signals`.

Verifies that each signal has a receiver, and that a plugin sends the
lifecycle signals, with the arguments that the signals document.
"""

from unittest import mock

from django.dispatch import Signal

from smarter.apps.plugin import signals
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.plugin.plugin.tests.base_classes import capture_signal
from smarter.lib import logging

from .base_classes import PluginAppTestBase

logger = logging.getLogger(__name__)

SIGNAL_NAMES = (
    "plugin_created",
    "plugin_cloned",
    "plugin_updated",
    "plugin_deleted",
    "plugin_deleting",
    "plugin_called",
    "plugin_responded",
    "plugin_ready",
    "plugin_selected",
    "broker_ready",
    "websearch_searched",
    "websearch_fetched",
    "websearch_failed",
)
TASK_PATCH = "smarter.apps.plugin.receivers.create_plugin_selector_history"


class TestPluginSignals(PluginAppTestBase):
    """Test the plugin app's signals."""

    def test_signals(self):
        """Test that each signal is a Django Signal, with a receiver in smarter.apps.plugin.receivers."""
        for name in SIGNAL_NAMES:
            signal = getattr(signals, name)
            self.assertIsInstance(signal, Signal, name)
            self.assertTrue(signal.has_listeners(), name)

    def test_plugin_created(self):
        """Test that creating a plugin sends plugin_created."""
        name = "test_plugin_app_signals_created"
        with capture_signal(signals.plugin_created) as received:
            plugin = self.new_static_plugin(name)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0]["plugin"], plugin)
        self.assertEqual(received[0]["sender"], StaticPlugin)

    def test_plugin_ready(self):
        """Test that loading a plugin sends plugin_ready."""
        with capture_signal(signals.plugin_ready) as received:
            plugin = StaticPlugin(plugin_meta=self.static_plugin.plugin_meta, user_profile=self.user_profile)
            self.assertTrue(plugin.ready)
        self.assertTrue(any(item["plugin"] is plugin for item in received))

    def test_plugin_updated(self):
        """Test that updating a plugin from its manifest sends plugin_updated."""
        name = "test_plugin_app_signals_updated"
        self.new_static_plugin(name)
        with capture_signal(signals.plugin_updated) as received:
            plugin = StaticPlugin(manifest=self.static_manifest(name), user_profile=self.user_profile)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0]["plugin"], plugin)

    def test_plugin_deleted(self):
        """Test that deleting a plugin sends plugin_deleting, and then plugin_deleted."""
        name = "test_plugin_app_signals_deleted"
        plugin = self.new_static_plugin(name)
        plugin_meta = plugin.plugin_meta
        with capture_signal(signals.plugin_deleting) as deleting, capture_signal(signals.plugin_deleted) as deleted:
            self.assertTrue(plugin.delete())
        self.assertEqual(len(deleting), 1)
        self.assertEqual(deleting[0]["plugin_meta"], plugin_meta)
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]["plugin_name"], name)

    def test_plugin_cloned(self):
        """Test that cloning a plugin sends plugin_cloned."""
        name = "test_plugin_app_signals_cloned"
        clone_name = "test_plugin_app_signals_clone"
        plugin = self.new_static_plugin(name)
        self.addCleanup(self.delete_plugin_by_name, clone_name)
        with capture_signal(signals.plugin_cloned) as received:
            plugin.clone(new_name=clone_name)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0]["plugin"], plugin)

    def test_plugin_called_and_responded(self):
        """Test that a tool call sends plugin_called, and then plugin_responded with the response."""
        with (
            capture_signal(signals.plugin_called) as called,
            capture_signal(signals.plugin_responded) as responded,
        ):
            response = self.static_plugin.tool_call_fetch_plugin_response({"inquiry_type": "couponCodes"})
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0]["inquiry_type"], "couponCodes")
        self.assertEqual(len(responded), 1)
        self.assertEqual(responded[0]["response"], response)

    def test_plugin_selected(self):
        """Test that selecting a plugin sends plugin_selected, with the search term."""
        plugin = StaticPlugin(plugin_meta=self.static_plugin.plugin_meta, user_profile=self.user_profile)
        with mock.patch(TASK_PATCH), capture_signal(signals.plugin_selected) as received:
            self.assertTrue(plugin.selected(user=self.admin_user, input_text="Where can I buy a Gobstopper?"))
        self.assertEqual(len(received), 1)
        self.assertIs(received[0]["plugin"], plugin)
        self.assertEqual(received[0]["search_term"], "Gobstopper")
        self.assertEqual(received[0]["user"], self.admin_user)

    def test_plugin_not_selected(self):
        """Test that a plugin is not selected, and sends nothing, when the input does not refer to it."""
        plugin = StaticPlugin(plugin_meta=self.static_plugin.plugin_meta, user_profile=self.user_profile)
        with mock.patch(TASK_PATCH), capture_signal(signals.plugin_selected) as received:
            self.assertFalse(plugin.selected(user=self.admin_user, input_text="What is the weather today?"))
        self.assertEqual(received, [])
