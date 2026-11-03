"""Test the doodle app's management commands, load_doodle_themes and plan_doodles."""

import io
import os
from unittest.mock import patch

from django.core.management import call_command, get_commands

from smarter.apps.doodle.models import DoodleTheme

from .mixins import DoodleTestMixin

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class TestDoodleCommands(DoodleTestMixin):
    """The commands that initialize_platform runs."""

    def test_the_commands_are_the_doodle_apps(self):
        commands = get_commands()
        self.assertEqual(commands["load_doodle_themes"], "smarter.apps.doodle")
        self.assertEqual(commands["plan_doodles"], "smarter.apps.doodle")

    def test_load_doodle_themes(self):
        out = io.StringIO()
        call_command("load_doodle_themes", stdout=out)
        self.assertIn(f"Loaded {len(self.themes)} doodle themes.", out.getvalue())

    def test_load_doodle_themes_fails_on_an_invalid_catalog(self):
        count = DoodleTheme.objects.count()
        with self.assertRaises(SystemExit):
            call_command("load_doodle_themes", folder=os.path.join(DATA, "invalid-region"), stdout=io.StringIO())
        self.assertEqual(DoodleTheme.objects.count(), count)

    def test_plan_doodles(self):
        out = io.StringIO()
        with patch("smarter.apps.doodle.management.commands.plan_doodles.plan_doodles", return_value=12) as plan:
            call_command("plan_doodles", days=3, stdout=out)
        plan.assert_called_once_with(days=3)
        self.assertIn("Planned 12 doodles.", out.getvalue())
