"""
Test the add_builtin_llmhost and add_builtin_llmhost_compute management commands.

Applying an LLMHost manifest does not launch it, but these tests still mock
apply_manifest and add_builtin_computes: the commands' own logic is what is
under test, and the manifests are tested by the llmhost manifest tests.
"""

import glob
import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from smarter.apps.account.models import User
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmhost.const import BUILTIN_MANIFESTS_PATH

COMMANDS = "smarter.apps.llmhost.management.commands"


class BuiltinCommandTestBase(TestAccountMixin):
    """Run a management command, and return its output."""

    def run_command(self, command_name: str, **options) -> str:
        out = StringIO()
        call_command(command_name, stdout=out, stderr=out, **options)
        return out.getvalue()


class TestAddBuiltinLLMHost(BuiltinCommandTestBase):
    """Test manage.py add_builtin_llmhost."""

    def setUp(self):
        super().setUp()
        self.manifests = sorted(glob.glob(os.path.join(BUILTIN_MANIFESTS_PATH, "*.yaml")))
        patcher = patch(f"{COMMANDS}.add_builtin_llmhost.call_command")
        self.apply_manifest = patcher.start()
        self.addCleanup(patcher.stop)

    def test_applies_every_builtin_manifest(self):
        self.assertTrue(self.manifests)
        output = self.run_command("add_builtin_llmhost", username=self.admin_user.username, verbose=True)
        applied = [call.kwargs["filespec"] for call in self.apply_manifest.call_args_list]
        self.assertEqual(applied, self.manifests)
        for call in self.apply_manifest.call_args_list:
            self.assertEqual(call.args, ("apply_manifest",))
            self.assertEqual(call.kwargs["username"], self.admin_user.username)
        self.assertIn(f"Applied {self.manifests[0]}", output)
        self.assertNotIn("failed to apply", output)

    def test_reports_manifests_that_fail(self):
        self.apply_manifest.side_effect = RuntimeError("invalid manifest")
        output = self.run_command("add_builtin_llmhost", username=self.admin_user.username)
        self.assertEqual(self.apply_manifest.call_count, len(self.manifests))
        self.assertIn("failed to apply", output)
        self.assertIn(f"{os.path.basename(self.manifests[0])}: invalid manifest", output)

    def test_unknown_user(self):
        """Get_cached_user_for_username() raises for an unknown user; the command also guards against None."""
        with self.assertRaises(User.DoesNotExist):
            self.run_command("add_builtin_llmhost", username=f"not_a_user_{self.hash_suffix}")
        with patch(f"{COMMANDS}.add_builtin_llmhost.get_cached_user_for_username", return_value=None):
            with self.assertRaises(SystemExit):
                self.run_command("add_builtin_llmhost", username=self.admin_user.username)
        self.apply_manifest.assert_not_called()


class TestAddBuiltinLLMHostCompute(BuiltinCommandTestBase):
    """Test manage.py add_builtin_llmhost_compute."""

    def setUp(self):
        super().setUp()
        patcher = patch(f"{COMMANDS}.add_builtin_llmhost_compute.add_builtin_computes", return_value=True)
        self.add_builtin_computes = patcher.start()
        self.addCleanup(patcher.stop)

    def test_add_builtin_computes(self):
        output = self.run_command("add_builtin_llmhost_compute", username=self.admin_user.username)
        self.add_builtin_computes.assert_called_once()
        self.assertEqual(self.add_builtin_computes.call_args.kwargs["user_profile"].user, self.admin_user)
        self.assertNotIn("failed to apply", output)

    def test_reports_failure(self):
        self.add_builtin_computes.return_value = False
        output = self.run_command("add_builtin_llmhost_compute", username=self.admin_user.username)
        self.assertIn("failed to apply", output)

    def test_error(self):
        self.add_builtin_computes.side_effect = RuntimeError("bad manifest")
        with self.assertRaises(SystemExit):
            self.run_command("add_builtin_llmhost_compute", username=self.admin_user.username)

    def test_unknown_user(self):
        """Get_cached_user_for_username() raises for an unknown user; the command also guards against None."""
        with self.assertRaises(User.DoesNotExist):
            self.run_command("add_builtin_llmhost_compute", username=f"not_a_user_{self.hash_suffix}")
        with patch(f"{COMMANDS}.add_builtin_llmhost_compute.get_cached_user_for_username", return_value=None):
            with self.assertRaises(SystemExit):
                self.run_command("add_builtin_llmhost_compute", username=self.admin_user.username)
        self.add_builtin_computes.assert_not_called()
