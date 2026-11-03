"""Test smarter.apps.account.user_merge: merging the users that share an email address."""

from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import Group
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from social_django.models import UserSocialAuth

from smarter.apps.account.models import AccountContact, User, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import DuplicateUsersMixin
from smarter.apps.account.user_merge import (
    MERGED_NAME_SUFFIX,
    UserMergeReport,
    clear_cache,
    create_unique_email_index,
    drop_unique_email_index,
    email_key,
    find_duplicate_users,
    historical_apps,
    merge_duplicate_users,
    merge_user_fields,
)
from smarter.apps.dashboard.models import OnboardingHint, OnboardingHints
from smarter.apps.secret.models import Secret

MODULE = "smarter.apps.account.user_merge"


class TestUserMerge(DuplicateUsersMixin):
    """Test that the users who share an email address are merged into the one who signed in last."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.apps = historical_apps()

    def setUp(self):
        super().setUp()
        self.email = f"Merge.{get_random_string(8)}@Example.com"
        self.now = timezone.now()

    def group_of(self, user: User) -> list:
        """Return the ids of the group of duplicates that includes the user, survivor first."""
        for group in find_duplicate_users(self.apps):
            ids = [member.pk for member in group]
            if user.pk in ids:
                return ids
        return []

    def report_of(self, reports: list[UserMergeReport], survivor: User) -> UserMergeReport:
        """Return the report of the merge that kept the survivor."""
        for report in reports:
            if report.survivor_id == survivor.pk:
                return report
        self.fail(f"no merge kept user {survivor.pk}")

    def secret(self, user_profile: UserProfile, name: str) -> Secret:
        """Create a Secret that the profile owns."""
        return Secret.objects.create(user_profile=user_profile, name=name, encrypted_value=Secret.encrypt("v"))

    def test_email_key_ignores_case_and_trailing_spaces(self):
        self.assertEqual(email_key("Bob@Example.COM  "), "bob@example.com")

    def test_survivor_signed_in_most_recently(self):
        never = self.duplicate_user(self.email)
        old = self.duplicate_user(self.email.lower(), last_login=self.now - timedelta(days=30))
        recent = self.duplicate_user(self.email.upper() + " ", last_login=self.now)
        self.assertEqual(self.group_of(old), [recent.pk, old.pk, never.pk])

    def test_survivor_is_the_oldest_when_none_signed_in(self):
        first = self.duplicate_user(self.email)
        second = self.duplicate_user(self.email)
        self.assertEqual(self.group_of(second), [first.pk, second.pk])

    def test_blank_addresses_are_not_duplicates(self):
        blank = self.duplicate_user("", with_profile=False)
        other_blank = self.duplicate_user("", with_profile=False)
        self.assertEqual(self.group_of(blank), [])
        self.assertEqual(self.group_of(other_blank), [])

    def test_merge_moves_the_profile_of_another_account(self):
        other_admin, other_account, _ = admin_user_factory()
        try:
            survivor = self.duplicate_user(self.email, last_login=self.now)
            duplicate = self.duplicate_user(self.email, account=other_account)
            reports = merge_duplicate_users(self.apps)

            report = self.report_of(reports, survivor)
            self.assertEqual(report.duplicate_ids, [duplicate.pk])
            self.assertFalse(User.objects.filter(pk=duplicate.pk).exists())
            accounts = set(UserProfile.objects.filter(user=survivor).values_list("account_id", flat=True))
            self.assertEqual(accounts, {self.account.pk, other_account.pk})
        finally:
            # not factory_account_teardown(): its sweep of test accounts would delete this class's account too.
            UserProfile.objects.filter(account=other_account).delete()
            AccountContact.objects.filter(account=other_account).delete()
            other_admin.delete()
            other_account.delete()

    def test_merge_profiles_in_the_same_account(self):
        survivor = self.duplicate_user(self.email, last_login=self.now)
        duplicate = self.duplicate_user(
            self.email.lower(), last_login=self.now - timedelta(days=1), password="the-old-password-1!"
        )
        duplicate.is_staff = True
        duplicate.date_joined = self.now - timedelta(days=365)
        duplicate.first_name = "Merged"
        duplicate.save()
        survivor_profile = UserProfile.objects.get(user=survivor)
        duplicate_profile = UserProfile.objects.get(user=duplicate)

        shared_name = f"merge_secret_{get_random_string(6).lower()}"
        survivor_secret = self.secret(survivor_profile, shared_name)
        clashing_secret = self.secret(duplicate_profile, shared_name)
        moved_secret = self.secret(duplicate_profile, f"{shared_name}_only")

        group, _ = Group.objects.get_or_create(name=f"merge_group_{get_random_string(6).lower()}")
        survivor.groups.add(group)
        duplicate.groups.add(group)
        OnboardingHint.objects.create(user=survivor, hint=OnboardingHints.WORKBENCH_TOUR, outcome="dismissed")
        OnboardingHint.objects.create(user=duplicate, hint=OnboardingHints.WORKBENCH_TOUR, outcome="completed")
        social = UserSocialAuth.objects.create(user=duplicate, provider="github", uid=get_random_string(12))

        try:
            reports = merge_duplicate_users(self.apps)
            report = self.report_of(reports, survivor)

            self.assertFalse(User.objects.filter(pk=duplicate.pk).exists())
            self.assertFalse(UserProfile.objects.filter(pk=duplicate_profile.pk).exists())
            self.assertIn(f"account.UserProfile {duplicate_profile.pk}", report.deleted)

            survivor_secret.refresh_from_db()
            clashing_secret.refresh_from_db()
            moved_secret.refresh_from_db()
            self.assertEqual(survivor_secret.name, shared_name)
            self.assertEqual(clashing_secret.user_profile_id, survivor_profile.pk)
            self.assertEqual(clashing_secret.name, f"{shared_name}{MERGED_NAME_SUFFIX}{clashing_secret.pk}")
            self.assertEqual(moved_secret.user_profile_id, survivor_profile.pk)
            self.assertEqual(len(report.renamed), 1)

            self.assertEqual(list(survivor.groups.all()), [group])
            hints = OnboardingHint.objects.filter(user=survivor)
            self.assertEqual(list(hints.values_list("outcome", flat=True)), ["dismissed"])
            social.refresh_from_db()
            self.assertEqual(social.user_id, survivor.pk)

            survivor.refresh_from_db()
            self.assertTrue(survivor.check_password("the-old-password-1!"))
            self.assertTrue(survivor.is_staff)
            self.assertEqual(survivor.first_name, "Merged")
            self.assertEqual(survivor.date_joined, duplicate.date_joined)
            self.assertEqual(survivor.last_login, self.now)
        finally:
            Secret.objects.filter(pk__in=[survivor_secret.pk, clashing_secret.pk, moved_secret.pk]).delete()
            group.delete()

    def test_merge_keeps_the_survivors_usable_password(self):
        survivor = self.duplicate_user(self.email, last_login=self.now, password="the-new-password-1!")
        self.duplicate_user(self.email, last_login=self.now - timedelta(days=1), password="the-old-password-1!")
        merge_duplicate_users(self.apps)
        survivor.refresh_from_db()
        self.assertTrue(survivor.check_password("the-new-password-1!"))

    def test_merge_user_fields_takes_a_later_last_login(self):
        user_model = self.apps.get_model("auth", "User")
        survivor = user_model(last_login=None, date_joined=self.now, password="!", is_active=False)
        duplicate = user_model(last_login=self.now, date_joined=self.now, password="!", is_active=True)
        duplicate.is_superuser = True
        merge_user_fields(survivor, duplicate)
        self.assertEqual(survivor.last_login, self.now)
        self.assertTrue(survivor.is_active)
        self.assertTrue(survivor.is_superuser)

    def test_dry_run_changes_nothing(self):
        survivor = self.duplicate_user(self.email, last_login=self.now)
        duplicate = self.duplicate_user(self.email)
        reports = merge_duplicate_users(self.apps, dry_run=True)
        report = self.report_of(reports, survivor)
        self.assertEqual(report.duplicate_ids, [duplicate.pk])
        self.assertTrue(User.objects.filter(pk=duplicate.pk).exists())
        self.assertTrue(UserProfile.objects.filter(user=duplicate).exists())
        merge_duplicate_users(self.apps)

    def test_merge_clears_the_cache(self):
        self.duplicate_user(self.email, last_login=self.now)
        self.duplicate_user(self.email)
        with mock.patch(f"{MODULE}.call_command") as call_command:
            merge_duplicate_users(self.apps)
        call_command.assert_called_once_with("reset_cache")

    def test_clear_cache_logs_a_failure(self):
        with mock.patch(f"{MODULE}.call_command", side_effect=SystemExit(1)):
            with self.assertLogs(MODULE, level="WARNING") as logs:
                clear_cache()
        self.assertIn("could not clear the cache", logs.output[0])

    def test_summary(self):
        report = UserMergeReport(email="m***@example.com", survivor_id=7, duplicate_ids=[9], moved=["x 1"])
        self.assertEqual(
            report.summary(), "m***@example.com: kept user 7, merged users [9]: 1 moved, 0 renamed, 0 deleted"
        )

    def test_unique_index_with_duplicates_fails_and_can_be_retried(self):
        self.duplicate_user(self.email, with_profile=False)
        self.duplicate_user(self.email, with_profile=False)
        with self.assertRaises(IntegrityError):
            with connection.schema_editor(atomic=False) as editor:
                create_unique_email_index(editor)
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM auth_user LIKE 'email_unique'")
            self.assertEqual(cursor.fetchall(), ())

    def test_unique_index_rejects_duplicates_but_not_blanks(self):
        with connection.schema_editor(atomic=False) as editor:
            create_unique_email_index(editor)
        try:
            self.duplicate_user(self.email, with_profile=False)
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self.duplicate_user(self.email.upper() + " ", with_profile=False)
            self.duplicate_user("", with_profile=False)
            self.duplicate_user("", with_profile=False)
        finally:
            with connection.schema_editor(atomic=False) as editor:
                drop_unique_email_index(editor)
