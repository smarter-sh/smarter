"""Test the update_console_messages management command."""

import io
import os
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command

from smarter.apps.dashboard.management.commands import update_console_messages
from smarter.lib.unittest.base_classes import SmarterTestBase

COMMAND = "smarter.apps.dashboard.management.commands.update_console_messages"


class TestUpdateConsoleMessages(SmarterTestBase):
    """Test that the command runs makemessages for both domains, then compilemessages, in the right places."""

    def run_command(self, *args) -> list[tuple[str, dict, str]]:
        """Run the command with Django's commands faked, and return each call, and the directory it ran in."""
        calls: list[tuple[str, dict, str]] = []

        def fake_call_command(name, **kwargs):
            calls.append((name, kwargs, os.getcwd()))

        cwd = os.getcwd()
        with patch(f"{COMMAND}.call_command", side_effect=fake_call_command):
            call_command("update_console_messages", *args, stdout=io.StringIO())
        self.assertEqual(os.getcwd(), cwd, "the command must restore the working directory")
        return calls

    def test_updates_both_domains_and_compiles(self):
        """It updates django.po from the project, djangojs.po from react/i18n, then compiles them."""
        calls = self.run_command()
        project_root = Path(settings.PROJECT_ROOT).resolve()
        languages = [code for code, _ in settings.LANGUAGES]

        self.assertEqual([name for name, _, _ in calls], ["makemessages", "makemessages", "compilemessages"])

        _, django_kwargs, django_cwd = calls[0]
        self.assertEqual(django_kwargs["domain"], "django")
        self.assertEqual(django_kwargs["locale"], languages)
        self.assertEqual(django_kwargs["ignore_patterns"], update_console_messages.DJANGO_IGNORE_PATTERNS)
        self.assertEqual(Path(django_cwd).resolve(), project_root)

        _, js_kwargs, js_cwd = calls[1]
        self.assertEqual(js_kwargs["domain"], "djangojs")
        self.assertTrue(js_kwargs["no_location"])
        self.assertEqual(Path(js_cwd).resolve(), project_root / update_console_messages.REACT_MESSAGES_DIR)

        _, compile_kwargs, compile_cwd = calls[2]
        self.assertEqual(compile_kwargs["locale"], languages)
        self.assertEqual(Path(compile_cwd).resolve(), project_root)

    def test_one_language(self):
        """--language limits it to the languages given."""
        calls = self.run_command("--language", "es")
        for _, kwargs, _ in calls:
            self.assertEqual(kwargs["locale"], ["es"])

    def test_no_compile(self):
        """--no-compile skips compilemessages."""
        calls = self.run_command("--no-compile")
        self.assertEqual([name for name, _, _ in calls], ["makemessages", "makemessages"])

    def test_restores_the_working_directory_after_a_failure(self):
        """A failing makemessages doesn't leave the process in another directory."""
        cwd = os.getcwd()
        with patch(f"{COMMAND}.call_command", side_effect=RuntimeError("xgettext failed")):
            with self.assertRaises(RuntimeError):
                call_command("update_console_messages", stdout=io.StringIO())
        self.assertEqual(os.getcwd(), cwd)
