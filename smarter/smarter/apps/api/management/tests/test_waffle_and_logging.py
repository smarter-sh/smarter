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
