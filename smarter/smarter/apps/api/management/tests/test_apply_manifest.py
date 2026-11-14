"""Test the apply_manifest management command."""

import os
from unittest.mock import MagicMock, patch

from django.core.management import CommandError

from smarter.apps.guardrail.models import Guardrail
from smarter.common.exceptions import SmarterValueError

from .base import CommandTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
GUARDRAIL_MANIFEST = os.path.join(
    HERE, "..", "..", "..", "guardrail", "manifest", "brokers", "tests", "data", "guardrail.yaml"
)
BROKER = "smarter.apps.guardrail.manifest.brokers.guardrail.SAMGuardrailBroker.apply"


class TestApplyManifestCommand(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.addCleanup(Guardrail.objects.filter(name="test_guardrail", user_profile=self.user_profile).delete)

    def test_apply_file(self):
        self.run_command("apply_manifest", filespec=GUARDRAIL_MANIFEST, username=self.admin_user.username)
        self.assertTrue(Guardrail.objects.filter(name="test_guardrail", user_profile=self.user_profile).exists())

    def test_apply_manifest_text_verbose(self):
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
            self.run_command("apply_manifest", manifest=f.read(), username=self.admin_user.username, verbose=True)
        self.assertTrue(Guardrail.objects.filter(name="test_guardrail", user_profile=self.user_profile).exists())

    def test_invalid_arguments(self):
        self.run_command("apply_manifest", filespec=GUARDRAIL_MANIFEST)
        with self.assertRaises(SystemExit):
            self.run_command("apply_manifest", filespec=GUARDRAIL_MANIFEST, username="not_a_user")
        with self.assertRaises(SmarterValueError):
            self.run_command("apply_manifest", filespec="/not/a/file.yaml", username=self.admin_user.username)
        with self.assertRaises(SmarterValueError):
            self.run_command("apply_manifest", username=self.admin_user.username)

    def test_apply_in_one_of_the_users_accounts(self):
        """Test that --account_number applies the manifest as the user's profile in that account, of several."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.account.models import UserProfile
        from smarter.apps.account.tests.factories import mortal_user_factory

        _, other_account, _ = mortal_user_factory()
        other_profile = UserProfile.objects.create(
            user=self.admin_user, account=other_account, name=f"{self.admin_user.username}_other"
        )
        self.addCleanup(Guardrail.objects.filter(name="test_guardrail", user_profile=other_profile).delete)
        self.run_command(
            "apply_manifest",
            filespec=GUARDRAIL_MANIFEST,
            username=self.admin_user.username,
            account_number=other_account.account_number,
        )
        self.assertTrue(Guardrail.objects.filter(name="test_guardrail", user_profile=other_profile).exists())
        self.assertFalse(Guardrail.objects.filter(name="test_guardrail", user_profile=self.user_profile).exists())

        # an account that the user doesn't belong to applies nothing.
        self.run_command(
            "apply_manifest",
            filespec=GUARDRAIL_MANIFEST,
            username=self.non_admin_user.username,
            account_number=other_account.account_number,
        )
        self.assertFalse(
            Guardrail.objects.filter(name="test_guardrail", user_profile__user=self.non_admin_user).exists()
        )

    def test_unknown_kind(self):
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
            text = f.read().replace("kind: Guardrail", "kind: NotAKind")
        self.run_command("apply_manifest", manifest=text, username=self.admin_user.username)

    def test_apply_failure(self):
        """Test that a failed apply, or no response from the broker, is a CommandError."""
        for response in (MagicMock(status_code=400, content=b"bad"), None):
            with self.subTest(response=response), patch(BROKER, return_value=response):
                with self.assertRaises(CommandError):
                    self.run_command("apply_manifest", filespec=GUARDRAIL_MANIFEST, username=self.admin_user.username)

    def test_verbose_is_a_flag(self):
        """Test that --verbose is a flag, which takes no value."""
        from smarter.apps.api.management.commands.apply_manifest import (  # pylint: disable=import-outside-toplevel
            Command,
        )

        parser = Command().create_parser("manage.py", "apply_manifest")
        self.assertTrue(parser.parse_args(["--verbose"]).verbose)
        self.assertFalse(parser.parse_args([]).verbose)
