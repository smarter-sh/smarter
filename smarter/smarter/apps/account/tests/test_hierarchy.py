"""
Test :mod:`smarter.apps.account.hierarchy`, and the account tree's fields on :class:`Account`.

The tree is a small organization, as in ADR-036's worked example::

    Smarter (the root, shares with everyone)
    ├── Corp            shares nothing
    │   ├── IT          shares with Corp's subtree
    │   └── HR          shares nothing
    └── Outsider        another company, shares nothing

Resources are Secrets, read through the generic permission queryset: Secret's own queryset hides other
users' secrets, as :mod:`smarter.apps.account.tests.test_metadata_with_ownership` explains.
"""

from django.utils.crypto import get_random_string

from smarter.apps.account.hierarchy import (
    ancestor_ids,
    readable_account_ids,
    resolve_by_name,
    root_account_id,
)
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.models.metadata_with_ownership import (
    SmarterQuerySetWithPermissions,
)
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.secret.models import Secret
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestAccountHierarchy(SmarterTestBase):
    """Test the tree's validation, the readable accounts, the read rule, name resolution and invalidation."""

    corp: Account
    it: Account
    hr: Account
    outsider: Account
    corp_profile: UserProfile
    it_profile: UserProfile
    hr_profile: UserProfile
    outsider_profile: UserProfile

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _, cls.corp, cls.corp_profile = mortal_user_factory()
        _, cls.it, cls.it_profile = mortal_user_factory()
        _, cls.hr, cls.hr_profile = mortal_user_factory()
        _, cls.outsider, cls.outsider_profile = mortal_user_factory()

        cls.it.parent = cls.corp
        cls.it.share_scope = cls.corp
        cls.it.save()
        cls.hr.parent = cls.corp
        cls.hr.save()

    @classmethod
    def tearDownClass(cls):
        profiles = [cls.corp_profile, cls.it_profile, cls.hr_profile, cls.outsider_profile]
        for profile in profiles:
            user = profile.user
            profile.delete()
            User.objects.filter(pk=user.pk).delete()
        # children first: a parent with children is protected.
        for account in [cls.it, cls.hr, cls.corp, cls.outsider]:
            Account.objects.filter(pk=account.pk).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.name = f"test_hierarchy_{get_random_string(8).lower()}"
        self.readable: SmarterQuerySetWithPermissions[Secret] = SmarterQuerySetWithPermissions(Secret)

    def secret(self, user_profile: UserProfile, name: str) -> Secret:
        """Create a secret that the test deletes afterwards."""
        secret = Secret.objects.create(user_profile=user_profile, name=name, encrypted_value=Secret.encrypt("v"))
        self.addCleanup(Secret.objects.filter(pk=secret.pk).delete)
        return secret

    def reload(self, account: Account) -> Account:
        """The account as it is in the database."""
        return Account.objects.get(pk=account.pk)

    def test_root_shares_with_everyone(self):
        """Test that the Smarter account is the root, and shares with itself."""
        root = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        self.assertTrue(root.is_root)
        self.assertIsNone(root.parent_id)  # type: ignore[attr-defined]
        self.assertEqual(root.share_scope_id, root.pk)  # type: ignore[attr-defined]
        self.assertEqual(root_account_id(), root.pk)
        self.assertFalse(self.corp.is_root)

    def test_ancestor_ids(self):
        """Test that an account's ancestors end with the root, also when its parent is null."""
        root_id = root_account_id()
        self.assertEqual(ancestor_ids(self.hr.pk), [self.hr.pk, self.corp.pk, root_id])
        self.assertEqual(ancestor_ids(self.outsider.pk), [self.outsider.pk, root_id])
        self.assertEqual(ancestor_ids(root_id), [root_id])  # type: ignore[arg-type]

    def test_ancestor_ids_refuses_a_cycle(self):
        """Test that a cycle made by a direct database edit is reported, not walked forever."""
        Account.objects.filter(pk=self.corp.pk).update(parent=self.hr)
        self.addCleanup(Account.objects.filter(pk=self.corp.pk).update, parent=None)
        with self.assertRaises(ValueError):
            ancestor_ids(self.hr.pk)

    def test_readable_account_ids(self):
        """Test that each account reads itself first, then the nearest sharing accounts, then the root."""
        root_id = root_account_id()
        hr_readable = readable_account_ids(self.hr.pk)
        self.assertEqual(hr_readable[:2], (self.hr.pk, self.it.pk))
        self.assertEqual(hr_readable[-1], root_id)
        self.assertEqual(readable_account_ids(self.corp.pk)[:2], (self.corp.pk, self.it.pk))
        self.assertNotIn(self.it.pk, readable_account_ids(self.outsider.pk))
        self.assertIn(root_id, readable_account_ids(self.outsider.pk))
        # IT reads its own resources once, though it shares with its own ancestor.
        self.assertEqual(readable_account_ids(self.it.pk).count(self.it.pk), 1)

    def test_read_rule(self):
        """Test that shared resources reach the subtree only, and that nothing is shared upward."""
        it_secret = self.secret(self.it_profile, self.name)
        hr_secret = self.secret(self.hr_profile, f"{self.name}_hr")

        self.assertIn(it_secret, self.readable.with_read_permission_for(self.hr_profile.user))
        self.assertIn(it_secret, self.readable.with_read_permission_for(self.corp_profile.user))
        self.assertNotIn(it_secret, self.readable.with_read_permission_for(self.outsider_profile.user))

        self.assertNotIn(hr_secret, self.readable.with_read_permission_for(self.corp_profile.user))
        self.assertNotIn(hr_secret, self.readable.with_read_permission_for(self.it_profile.user))
        self.assertIn(hr_secret, self.readable.with_read_permission_for(self.hr_profile.user))

    def test_resolve_by_name_nearest_wins(self):
        """Test that a department's own resource wins over a shared one of the same name."""
        it_secret = self.secret(self.it_profile, self.name)
        hr_secret = self.secret(self.hr_profile, self.name)

        self.assertEqual(resolve_by_name(self.readable, self.name, self.hr_profile), hr_secret)
        self.assertEqual(resolve_by_name(self.readable, self.name, self.corp_profile), it_secret)

        Secret.objects.filter(pk=hr_secret.pk).delete()
        self.assertEqual(resolve_by_name(self.readable, self.name, self.hr_profile), it_secret)

    def test_resolve_by_name_not_shared(self):
        """Test that another company can't resolve a resource that isn't shared with it."""
        self.secret(self.it_profile, self.name)
        with self.assertRaises(Secret.DoesNotExist):
            resolve_by_name(self.readable, self.name, self.outsider_profile)

    def test_resolve_by_name_follows_the_tree_only(self):
        """Test that resolution ignores what the user reads through superuser status or other profiles."""
        self.secret(self.it_profile, self.name)
        outsider_user = self.outsider_profile.user
        # the outsider also belongs to IT, and is a superuser: neither reaches their outside account's resources.
        it_membership = UserProfile.objects.create(user=outsider_user, account=self.it, name=f"{self.name}_member")
        self.addCleanup(UserProfile.objects.filter(pk=it_membership.pk).delete)
        User.objects.filter(pk=outsider_user.pk).update(is_superuser=True)
        self.addCleanup(User.objects.filter(pk=outsider_user.pk).update, is_superuser=False)
        outsider_profile = UserProfile.objects.select_related("user").get(pk=self.outsider_profile.pk)

        self.assertTrue(self.readable.with_read_permission_for(outsider_profile.user).filter(name=self.name).exists())
        with self.assertRaises(Secret.DoesNotExist):
            resolve_by_name(self.readable, self.name, outsider_profile)

    def test_change_of_share_scope_invalidates(self):
        """Test that unsharing takes effect at once, through the cache."""
        it_secret = self.secret(self.it_profile, self.name)
        self.assertIn(it_secret, self.readable.with_read_permission_for(self.hr_profile.user))

        it = self.reload(self.it)
        it.share_scope = None
        it.save()
        self.addCleanup(self.share_it_with_corp)
        self.assertNotIn(self.it.pk, readable_account_ids(self.hr.pk))
        self.assertNotIn(it_secret, self.readable.with_read_permission_for(self.hr_profile.user))

    def share_it_with_corp(self):
        """Restore IT's sharing."""
        it = self.reload(self.it)
        it.share_scope = self.corp
        it.save()

    def test_delete_of_sharing_account_invalidates(self):
        """Test that deleting an account that shares removes it from the readable accounts."""
        _, facilities, facilities_profile = mortal_user_factory()
        facilities.parent = self.corp
        facilities.share_scope = self.corp
        facilities.save()
        self.assertIn(facilities.pk, readable_account_ids(self.hr.pk))

        user = facilities_profile.user
        facilities_profile.delete()
        user.delete()
        facilities_pk = facilities.pk
        facilities.delete()
        self.assertNotIn(facilities_pk, readable_account_ids(self.hr.pk))

    def test_share_scope_must_be_self_or_ancestor(self):
        """Test that an account can't share with a sibling's subtree, or with another company."""
        hr = self.reload(self.hr)
        hr.share_scope = self.it
        with self.assertRaises(SmarterValueError):
            hr.save()
        hr.share_scope = self.outsider
        with self.assertRaises(SmarterValueError):
            hr.save()

    def test_share_scope_may_be_self_or_root(self):
        """Test that an account may share with its own subtree, or with every account under the root."""
        hr = self.reload(self.hr)
        self.addCleanup(Account.objects.filter(pk=self.hr.pk).update, share_scope=None)
        hr.share_scope = hr
        hr.save()
        hr.share_scope = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        hr.save()
        self.assertIn(self.hr.pk, readable_account_ids(self.outsider.pk))
        hr.share_scope = None
        hr.save()

    def test_no_cycles(self):
        """Test that an account can't be its own parent, or its descendant's child."""
        corp = self.reload(self.corp)
        corp.parent = corp
        with self.assertRaises(SmarterValueError):
            corp.save()
        corp.parent = self.hr
        with self.assertRaises(SmarterValueError):
            corp.save()

    def test_root_always_shares_with_everyone(self):
        """Test that saving the root without a share_scope makes it share with itself again."""
        root = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        self.addCleanup(Account.objects.filter(pk=root.pk).update, share_scope_id=root.pk)
        root.share_scope = None
        root.save()
        self.assertEqual(root.share_scope_id, root.pk)  # type: ignore[attr-defined]
        self.assertEqual(self.reload(root).share_scope_id, root.pk)  # type: ignore[attr-defined]

    def test_save_under_a_cycle_is_refused(self):
        """Test that an account can't be moved under a part of the tree that a direct database edit broke."""
        Account.objects.filter(pk=self.corp.pk).update(parent=self.hr)
        self.addCleanup(Account.objects.filter(pk=self.corp.pk).update, parent=None)
        outsider = self.reload(self.outsider)
        outsider.parent = self.hr
        with self.assertRaisesRegex(SmarterValueError, "cycle"):
            outsider.save()

    def test_root_has_no_parent(self):
        """Test that the root can't be moved under another account."""
        root = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        root.parent = self.corp
        with self.assertRaises(SmarterValueError):
            root.save()

    def test_hierarchy_changed(self):
        """Test which saves change the tree."""
        corp = self.reload(self.corp)
        self.assertFalse(corp.hierarchy_changed(self.reload(self.corp)))
        corp.parent = self.outsider
        self.assertTrue(corp.hierarchy_changed(self.reload(self.corp)))
        self.assertTrue(self.reload(self.it).hierarchy_changed(None))
        self.assertFalse(self.reload(self.outsider).hierarchy_changed(None))
