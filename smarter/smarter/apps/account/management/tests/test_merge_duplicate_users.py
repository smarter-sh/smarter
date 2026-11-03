"""Test the merge_duplicate_users management command."""

from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from django.utils.crypto import get_random_string

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.tests.mixins import DuplicateUsersMixin
from smarter.apps.secret.models import Secret


class TestMergeDuplicateUsers(DuplicateUsersMixin):
    """Test that the command reports a merge with --dry-run, and merges without it."""

    def setUp(self):
        super().setUp()
        email = f"Command.{get_random_string(8)}@Example.com"
        self.survivor = self.duplicate_user(email, last_login=timezone.now())
        self.duplicate = self.duplicate_user(email.lower())
        name = f"merge_command_{get_random_string(6).lower()}"
        survivor_profile = UserProfile.objects.get(user=self.survivor)
        duplicate_profile = UserProfile.objects.get(user=self.duplicate)
        self.secrets = [
            Secret.objects.create(user_profile=survivor_profile, name=name, encrypted_value=Secret.encrypt("v")),
            Secret.objects.create(user_profile=duplicate_profile, name=name, encrypted_value=Secret.encrypt("v")),
        ]

    def tearDown(self):
        Secret.objects.filter(pk__in=[secret.pk for secret in self.secrets]).delete()
        super().tearDown()

    def run_command(self, *args) -> str:
        out = StringIO()
        call_command("merge_duplicate_users", *args, stdout=out, stderr=out)
        return out.getvalue()

    def test_dry_run_reports_without_merging(self):
        output = self.run_command("--dry-run", "--verbose")
        self.assertIn(f"kept user {self.survivor.pk}, merged users [{self.duplicate.pk}]", output)
        self.assertIn("renamed secret.Secret", output)
        self.assertIn("deleted account.UserProfile", output)
        self.assertIn("would be merged", output)
        self.assertTrue(User.objects.filter(pk=self.duplicate.pk).exists())

    def test_merge(self):
        output = self.run_command()
        self.assertIn("were merged", output)
        self.assertNotIn("deleted account.UserProfile", output)
        self.assertFalse(User.objects.filter(pk=self.duplicate.pk).exists())
        again = self.run_command()
        self.assertNotIn(f"kept user {self.survivor.pk}", again)
