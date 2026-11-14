"""
Test :mod:`smarter.apps.account.tests.cleanup`.

The purge deletes every test account and user in the database, so this class has no class fixtures: each test
makes the leftovers that it purges, as a test that stopped halfway would have left them.
"""

from unittest import mock

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.tests.cleanup import (
    ACCOUNT_ADMIN_USERNAME_PATTERN,
    ADMIN_ACCOUNT_NAME_PREFIX,
    MORTAL_USERNAME_PREFIX,
    TEST_ACCOUNT_NAME_PREFIXES,
    TEST_USERNAME_PREFIXES,
    purge_test_artifacts,
)
from smarter.apps.account.tests.factories import (
    admin_user_factory,
    mortal_user_factory,
)
from smarter.apps.account.utils import (
    account_admin_username,
    get_cached_admin_user_for_account,
)
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestPurgeTestArtifacts(SmarterTestBase):
    """Test that the purge finds leftovers by the factories' marks, and keeps what isn't a test's."""

    def test_factories_use_the_marks(self):
        """The factories' accounts and users carry the prefixes that the purge looks for."""
        admin, admin_account, _ = admin_user_factory()
        mortal, mortal_account, _ = mortal_user_factory()
        self.addCleanup(purge_test_artifacts)
        self.assertTrue(admin_account.name.startswith(TEST_ACCOUNT_NAME_PREFIXES))
        self.assertTrue(mortal_account.name.startswith(TEST_ACCOUNT_NAME_PREFIXES))
        self.assertTrue(admin.username.startswith(TEST_USERNAME_PREFIXES))
        self.assertTrue(mortal.username.startswith(TEST_USERNAME_PREFIXES))

    def test_orphans_are_purged(self):
        """An account without members, and a user without a profile, are found and deleted."""
        admin, account, admin_profile = admin_user_factory()
        mortal, _, mortal_profile = mortal_user_factory(account=account)
        # a cleanup that stopped halfway: the profiles and the admin are gone, the account and a user stay.
        UserProfile.objects.filter(pk__in=[admin_profile.pk, mortal_profile.pk]).delete()
        User.objects.filter(pk=admin.pk).delete()

        report = purge_test_artifacts()

        self.assertFalse(Account.objects.filter(pk=account.pk).exists())
        self.assertFalse(User.objects.filter(pk=mortal.pk).exists())
        self.assertGreaterEqual(report.accounts, 1)
        self.assertGreaterEqual(report.users, 1)
        self.assertEqual(report.failures, [])

    def test_test_profiles_are_purged_with_their_users_and_accounts(self):
        """A test that never reached its teardown leaves profiles, which take their users and accounts along."""
        user, account, profile = mortal_user_factory()
        report = purge_test_artifacts()
        self.assertFalse(UserProfile.objects.filter(pk=profile.pk).exists())
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(Account.objects.filter(pk=account.pk).exists())
        self.assertGreaterEqual(report.profiles, 1)
        self.assertGreater(report.deleted, 0)

    def test_real_members_are_kept(self):
        """An account that a real user belongs to stays, and so does that user."""
        _, account, _ = admin_user_factory()
        real_user = User.objects.create_user(username=f"real_user_{self.hash_suffix}", password="x")
        self.addCleanup(User.objects.filter(pk=real_user.pk).delete)
        self.addCleanup(Account.objects.filter(pk=account.pk).delete)
        UserProfile.objects.create(user=real_user, account=account, name=real_user.username, is_test=False)
        self.addCleanup(UserProfile.objects.filter(user=real_user).delete)

        purge_test_artifacts()

        self.assertTrue(Account.objects.filter(pk=account.pk).exists())
        self.assertTrue(User.objects.filter(pk=real_user.pk).exists())

    def test_smarter_account_is_kept(self):
        """A test profile in the Smarter account is deleted, but never the account itself."""
        root = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        user, _, _ = mortal_user_factory(account=root)
        purge_test_artifacts()
        self.assertTrue(Account.objects.filter(pk=root.pk).exists())
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_a_failure_is_reported_not_raised(self):
        """A row that can't be deleted is reported by id and exception type, and the others are still deleted."""
        user, account, profile = admin_user_factory()
        UserProfile.objects.filter(pk=profile.pk).delete()
        self.addCleanup(purge_test_artifacts)
        with mock.patch.object(Account, "delete", side_effect=RuntimeError("names a user")):
            report = purge_test_artifacts()
        self.assertIn(f"Account id {account.pk}: RuntimeError", report.failures)
        self.assertNotIn("names a user", " ".join(report.failures))
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_orphaned_account_admins_are_purged(self):
        """An ``<account>-admin`` superuser whose account is gone is purged; one whose account exists is kept."""
        orphan = User.objects.create(username="0000-0000-0042-admin", is_superuser=True, is_staff=True)
        self.addCleanup(User.objects.filter(pk=orphan.pk).delete)
        root_admin_name = account_admin_username(SMARTER_ACCOUNT_NUMBER)
        kept = User.objects.filter(username=root_admin_name).first()
        if kept is None:
            kept = User.objects.create(username=root_admin_name)
            self.addCleanup(User.objects.filter(pk=kept.pk).delete)

        purge_test_artifacts()

        self.assertFalse(User.objects.filter(pk=orphan.pk).exists())
        self.assertTrue(User.objects.filter(pk=kept.pk).exists())
        self.assertIsNone(ACCOUNT_ADMIN_USERNAME_PATTERN.match("admin"))

    def test_deleting_an_account_deletes_its_created_admin(self):
        """The superuser that get_cached_admin_user_for_account() creates goes with its account."""
        account = Account.objects.create(name=f"test_cleanup_{self.hash_suffix}", company_name="Test Cleanup")
        self.addCleanup(Account.objects.filter(pk=account.pk).delete)
        created_admin = get_cached_admin_user_for_account(account=account)
        self.addCleanup(User.objects.filter(pk=created_admin.pk).delete)
        self.assertEqual(created_admin.username, account_admin_username(str(account.account_number)))
        self.assertTrue(created_admin.is_superuser)

        account.delete()

        self.assertFalse(User.objects.filter(pk=created_admin.pk).exists())

    def test_prefixes(self):
        """The prefixes are the ones the factories write."""
        self.assertIn(ADMIN_ACCOUNT_NAME_PREFIX, TEST_ACCOUNT_NAME_PREFIXES)
        self.assertIn(MORTAL_USERNAME_PREFIX, TEST_USERNAME_PREFIXES)
