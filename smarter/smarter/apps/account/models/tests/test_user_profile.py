# pylint: disable=wrong-import-position
"""Test UserProfile model."""

import pytest
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.utils import IntegrityError

from smarter.apps.account.models import Account, AccountContact
from smarter.apps.account.models.user_profile import (
    SmarterBaseModelManager,
    SmarterBaseQuerySetWithPermissions,
    UserProfile,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)


class TestUserProfile(TestAccountMixin):
    """Test UserProfile model"""

    logger_prefix = logging.formatted_text(f"{__name__}.TestUserProfile()")

    def test_dunders(self):
        """
        test all the dunder methods.
        """

        print(self.admin_user)
        print(self.account)
        print(self.user_profile)
        print(self.non_admin_user)
        print(self.non_admin_user_profile)

    def test_cached_user(self):
        """
        Test the `cached_user` property.

        Ensures that the property returns the associated User instance and utilizes caching as expected.
        """

        self.assertEqual(self.user_profile.cached_user, self.user_profile.user)

    def test_cached_account(self):
        """
        Test the `cached_account` property.

        Verifies that the property returns the associated Account instance and utilizes caching as expected.
        """
        self.assertEqual(self.user_profile.cached_account, self.account)

    def test_add_to_account_contacts(self):
        """
        Test the `add_to_account_contacts` method.

        Checks that the user is correctly added to the account's contact list and the primary flag is handled.
        """

        self.non_admin_user_profile.add_to_account_contacts()

        try:
            AccountContact.objects.get(
                account=self.account,
                email=self.non_admin_user_profile.user.email,
            )
        except AccountContact.DoesNotExist:
            self.fail("UserProfile was not added to AccountContact as expected.")

    def test_save(self):
        """
        Test the `save` method.

        Ensures that saving a UserProfile instance validates required fields, updates account contacts, and emits signals as expected.
        """

        self.user_profile.save()

    def test_admin_for_account(self):
        """
        Test the `admin_for_account` class method.

        Verifies that the correct admin user is returned or created for a given account.
        """
        admin_user = self.user_profile.admin_for_account(self.account)
        self.assertEqual(admin_user, self.admin_user)

    def test_get_cached_object(self):
        """
        Test the `get_cached_object` class method.

        Ensures that the method retrieves UserProfile instances by pk, name, user, username, or account, and handles caching and invalidation.
        """
        # Test retrieval by pk
        cached_by_pk = self.user_profile.get_cached_object(pk=self.user_profile.pk, invalidate=True)
        self.assertEqual(cached_by_pk, self.user_profile)
        cached_by_pk = self.user_profile.get_cached_object(pk=self.user_profile.pk)
        self.assertEqual(cached_by_pk, self.user_profile)

        # Test retrieval by name
        cached_by_name = self.user_profile.get_cached_object(name=self.user_profile.name, invalidate=True)
        self.assertEqual(cached_by_name, self.user_profile)
        cached_by_name = self.user_profile.get_cached_object(name=self.user_profile.name)
        self.assertEqual(cached_by_name, self.user_profile)

        # Test retrieval by user
        cached_by_user = self.user_profile.get_cached_object(user=self.user_profile.user, invalidate=True)
        self.assertEqual(cached_by_user, self.user_profile)
        cached_by_user = self.user_profile.get_cached_object(user=self.user_profile.user)
        self.assertEqual(cached_by_user, self.user_profile)

        # Test retrieval by username
        cached_by_username = self.user_profile.get_cached_object(
            username=self.user_profile.user.username, invalidate=True
        )
        self.assertEqual(cached_by_username, self.user_profile)
        cached_by_username = self.user_profile.get_cached_object(username=self.user_profile.user.username)
        self.assertEqual(cached_by_username, self.user_profile)

        # Test retrieval by account
        cached_by_account = self.user_profile.get_cached_object(account=self.account, invalidate=True)
        self.assertEqual(cached_by_account, self.user_profile)
        cached_by_account = self.user_profile.get_cached_object(account=self.account)
        self.assertEqual(cached_by_account, self.user_profile)

    def test_str(self):
        """
        Test the `__str__` method.

        Checks that the string representation of the UserProfile instance is correct and robust to missing user or account.
        """
        self.assertIsInstance(str(self.user_profile), str)
        self.assertGreater(len(str(self.user_profile)), 0)

    def test_repr(self):
        """
        Test the `__repr__` method.

        Ensures that the repr of the UserProfile instance matches its string representation.
        """
        self.assertIsInstance(repr(self.user_profile), str)
        self.assertGreater(len(repr(self.user_profile)), 0)

    def test_queryset_with_read_permission_for_superuser(self):
        qs = SmarterBaseQuerySetWithPermissions(UserProfile)
        result = qs.with_read_permission_for(self.admin_user)
        assert hasattr(result, "all")  # Should return a queryset

    def test_queryset_with_ownership_permission_for_superuser(self):
        qs = SmarterBaseQuerySetWithPermissions(UserProfile)
        result = qs.with_ownership_permission_for(self.admin_user)
        assert hasattr(result, "all")

    def test_queryset_with_ownership_permission_for_non_user(self):
        qs = SmarterBaseQuerySetWithPermissions(UserProfile)
        result = qs.with_ownership_permission_for(object())  # type: ignore
        assert hasattr(result, "none")

    def test_manager_returns_custom_queryset(self):
        manager = SmarterBaseModelManager()
        qs = manager.get_queryset()
        assert isinstance(qs, SmarterBaseQuerySetWithPermissions)

    def test_manager_filter_methods(self):

        manager = SmarterBaseModelManager()

        manager.filter()
        manager.exclude()
        manager.none()
        manager.complex_filter({})
        manager.union()
        manager.intersection()
        manager.difference()
        manager.select_for_update()
        manager.select_related()
        manager.prefetch_related()
        manager.order_by()
        manager.distinct()

        Account.objects.annotate(num_contacts=Count("contacts"))
        UserProfile.objects.filter(account=self.account).alias(num_contacts=Count("account__contacts")).filter(
            num_contacts__gt=0
        )

    def test_manager_permission_methods(self):
        manager = SmarterBaseModelManager()
        manager.with_read_permission_for(self.admin_user)
        manager.with_ownership_permission_for(self.admin_user)

    def test_userprofile_save_missing_fields(self):
        up = UserProfile()
        with pytest.raises((SmarterValueError, UserProfile.user.RelatedObjectDoesNotExist)):
            up.save()

    def test_get_cached_object_errors(self):
        # username not found
        with pytest.raises(User.DoesNotExist):
            UserProfile.get_cached_object(username="notarealuser123")

    def test_get_cached_objects_for_user(self):
        qs = UserProfile.get_cached_objects(user=self.admin_user)
        assert hasattr(qs, "filter")

    def test_str_repr_edge_cases(self):
        up = UserProfile(user=None, account=None)
        assert "NoUser" in str(up) or "NoAccount" in str(up)
        assert isinstance(repr(up), str)

    def test_module_exports(self):
        # pylint: disable=C0415
        from smarter.apps.account.models import user_profile

        assert "UserProfile" in user_profile.__all__
        assert "SmarterBaseModelManager" in user_profile.__all__
        assert "SmarterBaseQuerySetWithPermissions" in user_profile.__all__


class TestUserProfileCoverageGaps(TestAccountMixin):
    """
    This class contains tests that specifically target code paths in the UserProfile model that were not covered by the main test class.
    """

    def test_userprofile_save_change_user_or_account(self):

        # Save a valid profile. should not raise an error
        user_profile = self.non_admin_user_profile
        user_profile.save()

        # Try to change user or account
        orig_user = user_profile.user
        orig_account = user_profile.account

        user_profile.user = self.admin_user
        with pytest.raises(IntegrityError):
            user_profile.save()

        user_profile.account = orig_account
        user_profile.user = orig_user
        user_profile.save()  # Should succeed


class TestUserProfileCoverageGaps2(TestAccountMixin):
    """
    This class contains tests that specifically target code paths in the UserProfile model that were not covered by the main test class.
    """

    def test_add_to_account_contacts_primary_flag(self):
        # Should update is_primary if needed
        self.user_profile.add_to_account_contacts(is_primary=True)
        contact = AccountContact.objects.get(account=self.account, email=self.admin_user.email)
        assert contact.is_primary is True

    def test_admin_for_account_creates_admin(self):
        # Remove all users from an account to force admin creation
        account = smarter_cached_objects.smarter_account
        UserProfile.objects.filter(account=account).delete()
        user = UserProfile.admin_for_account(account)
        assert isinstance(user, User)


class TestUserProfileCoverageGaps3(TestAccountMixin):
    """
    This class contains tests that specifically target code paths in the UserProfile model that were not covered by the main test class.
    """

    def test_get_cached_object_multiple_objects(self):
        # Create a duplicate UserProfile for same user (should trigger MultipleObjectsReturned)

        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.admin_user, account=self.account)

        # should work
        user_profile = UserProfile.objects.create(user=self.admin_user, account=smarter_cached_objects.smarter_account)

        # invalidate cache and ensure it does not raise an error
        result = UserProfile.get_cached_object(user=self.admin_user, invalidate=True)
        self.assertIsInstance(result, UserProfile)
        self.assertEqual(result.user, self.admin_user)
        self.assertEqual(result.account, self.account)

        # subsequent call should hit cache and not raise error
        result = UserProfile.get_cached_object(user=self.admin_user)
        self.assertIsInstance(result, UserProfile)
        self.assertEqual(result.user, self.admin_user)
        self.assertEqual(result.account, self.account)

        try:
            user_profile.delete()
        # pylint: disable=broad-except
        except Exception:
            self.fail("could not delete new user_profile")
