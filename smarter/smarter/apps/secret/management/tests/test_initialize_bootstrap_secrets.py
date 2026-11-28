"""Test manage.py initialize_bootstrap_secrets: :mod:`smarter.apps.secret.management.commands.initialize_bootstrap_secrets`."""

import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.management.commands import initialize_bootstrap_secrets
from smarter.apps.secret.management.commands.initialize_bootstrap_secrets import (
    Command,
    bootstrap_files,
)
from smarter.apps.secret.models import Secret


class TestInitializeBootstrapSecrets(TestAccountMixin):
    """Each file of the bootstrap folder becomes the admin's Secret of its name; only names are logged (issue #1099)."""

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        self.name = f"test_bootstrap_{self.hash_suffix}"
        self.addCleanup(
            Secret.objects.filter(user_profile=self.user_profile, name__startswith="test_bootstrap_").delete
        )
        # the test account's user stands in for the Smarter admin.
        patcher = patch.object(
            initialize_bootstrap_secrets,
            "smarter_cached_objects",
            MagicMock(smarter_admin_user_profile=self.user_profile),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, name: str, text: str) -> None:
        with open(os.path.join(self.folder, name), "w", encoding="utf-8") as f:
            f.write(text)

    def run_command(self) -> None:
        Command(stdout=StringIO(), stderr=StringIO()).handle(folder=self.folder)

    def secret(self) -> Secret:
        return Secret.objects.get(user_profile=self.user_profile, name=self.name)

    def test_a_file_becomes_a_secret(self):
        """The file's text, without its trailing newline, is the Secret's value, encrypted."""
        self.write(self.name, "sk-bootstrap-value\n")
        self.run_command()
        self.assertEqual(self.secret().get_secret(), "sk-bootstrap-value")
        self.assertEqual(self.secret().description, initialize_bootstrap_secrets.DESCRIPTION)

    def test_a_changed_value_is_updated_and_an_unchanged_one_left_alone(self):
        """Every deploy runs it: an unchanged Secret isn't saved again; a changed one is, keeping its description."""
        self.write(self.name, "first")
        self.run_command()
        secret = self.secret()
        Secret.objects.filter(pk=secret.pk).update(description="set by an admin")
        with patch.object(Secret, "save") as save:
            self.run_command()
        save.assert_not_called()
        self.write(self.name, "second")
        self.run_command()
        self.assertEqual(self.secret().get_secret(), "second")
        self.assertEqual(self.secret().description, "set by an admin")

    def test_empty_files_and_placeholders_are_skipped(self):
        for text in ("", "  \n", "SET-ME-PLEASE"):
            with self.subTest(text=text):
                self.write(self.name, text)
                self.run_command()
                self.assertFalse(Secret.objects.filter(user_profile=self.user_profile, name=self.name).exists())

    def test_only_names_are_logged(self):
        self.write(self.name, "sk-never-logged")
        with patch.object(initialize_bootstrap_secrets.logger, "info") as info:
            self.run_command()
        logged = str(info.call_args_list)
        self.assertIn(self.name, logged)
        self.assertNotIn("sk-never-logged", logged)

    def test_a_kubernetes_secret_volume(self):
        """A mounted Kubernetes Secret's ..data and timestamped folder are left out; its visible names are read."""
        os.mkdir(os.path.join(self.folder, "..2026_11_28_12_00_00.000"))
        self.write("..data", "not a secret")
        self.write(self.name, "value")
        self.assertEqual(bootstrap_files(self.folder), [self.name])

    def test_a_missing_folder_is_nothing_to_do(self):
        self.assertEqual(bootstrap_files(os.path.join(self.folder, "no-such-folder")), [])
        Command(stdout=StringIO(), stderr=StringIO()).handle(folder=os.path.join(self.folder, "no-such-folder"))
