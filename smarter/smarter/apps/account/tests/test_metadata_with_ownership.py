"""
Test :mod:`smarter.apps.account.models.metadata_with_ownership`, with Secret, a direct subclass.

Each test gives its secrets new names: get_cached_object() caches a resource by its name and owner.
"""

from unittest.mock import PropertyMock, patch

from django.utils.crypto import get_random_string

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError


class TestMetaDataWithOwnership(TestAccountMixin):
    """Test the permission queryset, the manager's pass-throughs, the cached lookups and clone()."""

    def setUp(self):
        super().setUp()
        self.name = f"test_ownership_{get_random_string(8).lower()}"
        self.mine = self.secret(self.non_admin_user_profile, self.name)
        self.shared = self.secret(self.user_profile, f"{self.name}_shared")

    def secret(self, user_profile: UserProfile, name: str) -> Secret:
        secret = Secret.objects.create(user_profile=user_profile, name=name, encrypted_value=Secret.encrypt("v"))
        self.addCleanup(Secret.objects.filter(pk=secret.pk).delete)
        return secret

    def test_ownership(self):
        """Test that a customer owns their secrets, and their account admin's are shared with them."""
        user = self.non_admin_user
        self.assertIn(self.mine, Secret.objects.owned_by(user))
        self.assertNotIn(self.shared, Secret.objects.owned_by(user))
        self.assertIn(self.shared, Secret.objects.shared_with(user))
        self.assertIn(self.mine, Secret.objects.all().owned_by(user))
        self.assertIn(self.shared, Secret.objects.all().shared_with(user))
        self.assertIn(self.mine, Secret.objects.with_ownership_permission_for(user))
        self.assertNotIn(self.shared, Secret.objects.with_ownership_permission_for(user))

    def test_manager_passthroughs(self):
        """Test that the manager's queryset methods return the permission queryset."""
        qs = Secret.objects.filter(pk=self.mine.pk)
        self.assertEqual(list(Secret.objects.exclude(pk=self.shared.pk).filter(pk=self.mine.pk)), [self.mine])
        self.assertEqual(Secret.objects.none().count(), 0)
        self.assertEqual(Secret.objects.complex_filter({"pk": self.mine.pk}).get(), self.mine)
        self.assertEqual(Secret.objects.select_related("user_profile").filter(pk=self.mine.pk).get(), self.mine)
        self.assertEqual(Secret.objects.prefetch_related("tags").filter(pk=self.mine.pk).get(), self.mine)
        self.assertEqual(Secret.objects.annotate().filter(pk=self.mine.pk).get(), self.mine)
        self.assertEqual(Secret.objects.alias().filter(pk=self.mine.pk).get(), self.mine)
        self.assertEqual(Secret.objects.order_by("name").filter(pk=self.mine.pk).get(), self.mine)
        self.assertEqual(Secret.objects.distinct().filter(pk=self.mine.pk).get(), self.mine)
        self.assertEqual(Secret.objects.union(qs).count(), Secret.objects.count())
        self.assertEqual(Secret.objects.intersection(qs).count(), 1)
        self.assertEqual(Secret.objects.difference(qs).count(), Secret.objects.count() - 1)
        self.assertEqual(Secret.objects.select_for_update().filter(pk=self.mine.pk).query.select_for_update, True)

    def test_get_cached_object(self):
        """Test the cached lookups by pk, by name and owner, by name and account, and by username."""
        self.assertEqual(Secret.get_cached_object(pk=self.mine.pk, invalidate=True), self.mine)
        self.assertEqual(Secret.get_cached_object(pk=self.mine.pk, taggit=False, invalidate=True), self.mine)
        self.assertEqual(Secret.get_cached_object(name=self.name, user_profile=self.non_admin_user_profile), self.mine)
        self.assertEqual(
            Secret.get_cached_object(
                name=self.name, user_profile=self.non_admin_user_profile, taggit=False, invalidate=True
            ),
            self.mine,
        )
        self.assertEqual(Secret.get_cached_object(name=self.name, username=self.non_admin_user.username), self.mine)
        self.assertEqual(
            Secret.get_cached_object(name=self.name, user=self.non_admin_user, account=self.account), self.mine
        )
        with self.assertRaises(SmarterValueError):
            Secret.get_cached_object(pk="not an int")

    def test_get_cached_object_by_account(self):
        """Test the lookup by name and account, of a resource that the account's admin doesn't own."""
        self.assertEqual(Secret.get_cached_object(name=self.name, account=self.account, invalidate=True), self.mine)
        self.assertEqual(
            Secret.get_cached_object(name=self.name, account=self.account, taggit=False, invalidate=True), self.mine
        )

    def test_get_cached_objects(self):
        secrets = Secret.get_cached_objects(user_profile=self.non_admin_user_profile, invalidate=True)
        self.assertIn(self.mine, secrets)
        secrets = Secret.get_cached_objects(user_profile=self.non_admin_user_profile, invalidate=True, taggit=False)
        self.assertIn(self.mine, secrets)

    def test_clone(self):
        """Test that a clone has a new name, its owner may change, and an unnamed clone is suffixed."""
        clone = self.mine.clone(new_name=f"{self.name}_clone", user_profile=self.user_profile)
        self.addCleanup(Secret.objects.filter(pk=clone.pk).delete)
        self.assertEqual((clone.name, clone.user_profile), (f"{self.name}_clone", self.user_profile))
        self.assertEqual(clone.encrypted_value, self.mine.encrypted_value)
        unnamed = self.mine.clone()
        self.addCleanup(Secret.objects.filter(pk=unnamed.pk).delete)
        self.assertTrue(unnamed.name.startswith(self.name))
        self.assertNotEqual(unnamed.pk, self.mine.pk)
        self.assertIn(self.name, str(self.mine))
        self.assertIn(self.name, repr(self.mine))

    def test_save_invalidates_cache(self):
        self.assertEqual(Secret.get_cached_object(pk=self.mine.pk).description, self.mine.description)
        self.mine.description = "changed"
        self.mine.save()
        self.assertEqual(Secret.get_cached_object(pk=self.mine.pk).description, "changed")

    def test_user_without_profiles_has_no_permissions(self):
        """A user who has no user profile can read, and owns, nothing."""
        user = User.objects.create(username=f"test_no_profile_{self.hash_suffix}")
        self.addCleanup(user.delete)
        self.assertFalse(Secret.objects.all().with_read_permission_for(user).exists())
        self.assertFalse(Secret.objects.all().with_ownership_permission_for(user).exists())

    def test_authorize_a_resource_that_is_not_billable(self):
        with (
            patch.object(Secret, "is_billable_resource", new_callable=PropertyMock, return_value=False),
            patch("smarter.apps.account.models.metadata_with_ownership.charge_authorization") as charge,
        ):
            self.assertIsNone(self.mine.authorize())
        charge.assert_not_called()

    def test_get_cached_object_by_session_key_needs_the_field(self):
        with self.assertRaises(SmarterValueError):
            Secret.get_cached_object(session_key="0" * 64)

    def test_second_unnamed_clone_is_numbered(self):
        first = self.mine.clone()
        self.addCleanup(Secret.objects.filter(pk=first.pk).delete)
        second = self.mine.clone()
        self.addCleanup(Secret.objects.filter(pk=second.pk).delete)
        self.assertNotEqual(first.name, second.name)

    def test_save_ignores_lookups_that_find_nothing(self):
        with (
            patch.object(Secret, "get_cached_object", side_effect=[None, Secret.DoesNotExist, Secret.DoesNotExist]),
            patch.object(Secret, "get_cached_objects", side_effect=Secret.DoesNotExist),
        ):
            self.mine.description = "saved"
            self.mine.save()
        self.assertEqual(Secret.objects.get(pk=self.mine.pk).description, "saved")
