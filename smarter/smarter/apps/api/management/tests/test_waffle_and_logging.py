"""
Test the initialize_waffle and set_debug_logging management commands.

The database's switches are never changed: call_command and the Switch model are patched.
"""

import logging
from unittest.mock import MagicMock, patch

from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import CommandTestBase

WAFFLE = "smarter.apps.api.management.commands.initialize_waffle"
LOGGING = "smarter.apps.api.management.commands.set_debug_logging"


class TestInitializeWaffle(CommandTestBase):
    def test_creates_updates_and_deletes_switches(self):
        """Test that missing switches are created, notes are updated, and orphaned switches are deleted."""
        names = SmarterWaffleSwitches().all
        existing = MagicMock(note="an old note")
        existing.name = names[0]
        orphan = MagicMock()
        orphan.name = "an_orphaned_switch"
        switch = MagicMock()
        switch.objects.filter.side_effect = lambda name: MagicMock(exists=MagicMock(return_value=name == names[0]))
        switch.objects.get.side_effect = lambda name: existing if name == names[0] else MagicMock()
        switch.objects.all.return_value = [existing, orphan]
        with patch(f"{WAFFLE}.Switch", switch), patch(f"{WAFFLE}.call_command") as call, patch("builtins.print"):
            self.run_command("initialize_waffle")
        created = [c.args[1] for c in call.call_args_list if "--create" in c.args]
        self.assertEqual(len(created), len(names) - 1)
        self.assertNotEqual(existing.note, "an old note")
        existing.save.assert_called()
        orphan.delete.assert_called_once()
        existing.delete.assert_not_called()

    def check_reset(self, *args) -> list:
        """Run initialize_waffle against existing switches that are all inactive, and return the switches it set."""
        switches = {
            name: MagicMock(note=SmarterWaffleSwitches().switches[name].comment, active=False)
            for name in SmarterWaffleSwitches().all
        }
        switch = MagicMock()
        switch.objects.filter.return_value.exists.return_value = True
        switch.objects.get.side_effect = lambda name: switches[name]
        switch.objects.all.return_value = []
        with patch(f"{WAFFLE}.Switch", switch), patch(f"{WAFFLE}.call_command") as call, patch("builtins.print"):
            self.run_command("initialize_waffle", *args)
        return [
            c.args[1:] for c in call.call_args_list if c.args[1] != SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE
        ]

    def test_reset_sets_switches_to_their_defaults(self):
        """Test that --reset turns on the inactive switches whose default is active, and leaves the others."""
        defaults = SmarterWaffleSwitches().switches
        expected = [
            (name, "on")
            for name in SmarterWaffleSwitches().all
            if defaults[name].default and name != SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE
        ]
        changed = self.check_reset("--reset")
        self.assertIn((SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS, "on"), changed)
        self.assertCountEqual(changed, expected)

    def test_existing_switches_are_kept_without_reset(self):
        """Test that existing switches keep their state, which may have been changed in Django admin."""
        self.assertEqual(self.check_reset(), [])


class TestSetDebugLogging(CommandTestBase):
    def setUp(self):
        super().setUp()
        root = logging.getLogger()
        levels = (root.level, [handler.level for handler in root.handlers])

        def restore():
            root.setLevel(levels[0])
            for handler, level in zip(root.handlers, levels[1]):
                handler.setLevel(level)

        self.addCleanup(restore)

    def test_enable_and_disable(self):
        with patch(f"{LOGGING}.call_command") as call:
            self.run_command("set_debug_logging", enable=True)
            self.assertEqual(logging.getLogger().level, logging.DEBUG)
            self.run_command("set_debug_logging", disable=True)
            self.assertEqual(logging.getLogger().level, logging.INFO)
        self.assertEqual([c.args[2] for c in call.call_args_list], ["on", "off"])
