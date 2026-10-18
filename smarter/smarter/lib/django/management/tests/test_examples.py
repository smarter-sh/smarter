"""Test :class:`smarter.lib.django.management.examples.SmarterExamplesCommand`, the base of the add_example_<kinds> commands."""

import os
import tempfile
from io import StringIO
from typing import Optional
from unittest.mock import patch

from django.core.management import call_command

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.management.examples import SmarterExamplesCommand

MODULE = "smarter.lib.django.management.examples"


class ExamplesCommand(SmarterExamplesCommand):
    """An add_example_<kinds> command whose examples are ``filespecs``."""

    family = "Widget"
    filespecs: list[str] = []

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        return self.apply_all(self.filespecs, user_profile)  # type: ignore[arg-type]


class OwnerlessCommand(SmarterExamplesCommand):
    """An add_example_<kinds> command whose examples no user owns."""

    requires_owner = False

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        assert user_profile is None
        return []


class TestSmarterExamplesCommand(TestAccountMixin):
    """Test the owner, the applies, and the reporting of SmarterExamplesCommand."""

    def run_command(self, command: SmarterExamplesCommand, **options) -> str:
        call_command(command, **{"username": self.admin_user.username, **options})
        return command.output.getvalue()  # type: ignore[attr-defined]

    def command(self, *filespecs: str) -> ExamplesCommand:
        output = StringIO()
        command = ExamplesCommand(stdout=output, stderr=output)
        command.output = output  # type: ignore[attr-defined]
        command.filespecs = list(filespecs)
        return command

    def test_applies_each_manifest_as_the_user(self):
        with patch(f"{MODULE}.call_command") as call_command:
            output = self.run_command(self.command("a.yaml", "b.yaml"), verbose=True)
        self.assertEqual([call.kwargs["filespec"] for call in call_command.call_args_list], ["a.yaml", "b.yaml"])
        for call in call_command.call_args_list:
            self.assertEqual(call.args, ("apply_manifest",))
            self.assertEqual(call.kwargs["username"], self.admin_user.username)
        self.assertIn("Applied a.yaml", output)

    def test_defaults_to_the_smarter_admin(self):
        with patch(f"{MODULE}.call_command") as call_command:
            self.run_command(self.command("a.yaml"), username=None)
        self.assertNotEqual(call_command.call_args.kwargs["username"], self.admin_user.username)

    def test_failures_are_reported(self):
        """Test that a manifest that fails, by an exception or an exit, is reported, and the others applied."""
        with patch(f"{MODULE}.call_command", side_effect=[RuntimeError("boom"), SystemExit(1), None]):
            output = self.run_command(self.command("a.yaml", "b.yaml", "c.yaml"))
        self.assertIn("Example Widget manifests that failed to apply", output)
        self.assertIn("a.yaml: RuntimeError: boom", output)
        self.assertIn("b.yaml: SystemExit", output)
        self.assertIn("Applied c.yaml", output)

    def test_manifest_template_is_filled_in(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml.tpl", delete=False) as f:
            f.write("baseUrl: ${environment_platform_scheme}://${environment_platform_domain}\n")
        self.addCleanup(os.remove, f.name)
        with patch(f"{MODULE}.call_command") as call_command:
            self.run_command(self.command(f.name))
        self.assertNotIn("filespec", call_command.call_args.kwargs)
        self.assertNotIn("${", call_command.call_args.kwargs["manifest"])

    def test_given_manifest_is_applied(self):
        command = self.command()
        with patch(f"{MODULE}.call_command") as call_command:
            self.assertIsNone(command.apply("a.yaml", self.user_profile, manifest="kind: Widget"))
        self.assertEqual(call_command.call_args.kwargs["manifest"], "kind: Widget")

    def test_unknown_user(self):
        with self.assertRaises(SystemExit):
            self.run_command(self.command("a.yaml"), username="test_examples_no_such_user")

    def test_exception_fails_the_command(self):
        command = self.command()
        with (
            patch.object(ExamplesCommand, "add_examples", side_effect=RuntimeError("boom")),
            self.assertRaises(SystemExit),
        ):
            self.run_command(command)

    def test_ownerless_command_has_no_username(self):
        command = OwnerlessCommand(stdout=StringIO(), stderr=StringIO())
        parser = command.create_parser("manage.py", "add_example_widgets")
        self.assertNotIn("username", vars(parser.parse_args([])))
        call_command(command)

    def test_add_examples_is_abstract(self):
        with self.assertRaises(NotImplementedError):
            SmarterExamplesCommand().add_examples(user_profile=None)
