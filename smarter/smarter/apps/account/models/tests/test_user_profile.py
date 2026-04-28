# pylint: disable=wrong-import-position
"""Test UserProfile model."""

# our stuff
import logging

from smarter.apps.account.models import AccountContact
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)


class TestUserProfile(TestAccountMixin):
    """Test UserProfile model"""

    logger_prefix = formatted_text(f"{__name__}.TestUserProfile()")

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

        self.user_profile.add_to_account_contacts()

        try:
            AccountContact.objects.get(
                account=self.account,
                email=self.admin_user.email,
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
        cached_by_pk = self.user_profile.get_cached_object(pk=self.user_profile.pk)
        self.assertEqual(cached_by_pk, self.user_profile)

        # Test retrieval by name
        cached_by_name = self.user_profile.get_cached_object(name=self.user_profile.name)
        self.assertEqual(cached_by_name, self.user_profile)

        # Test retrieval by user
        cached_by_user = self.user_profile.get_cached_object(user=self.user_profile.user)
        self.assertEqual(cached_by_user, self.user_profile)

        # Test retrieval by username
        cached_by_username = self.user_profile.get_cached_object(username=self.user_profile.user.username)
        self.assertEqual(cached_by_username, self.user_profile)

        # Test retrieval by account
        cached_by_account = self.user_profile.get_cached_object(account=self.account)
        self.assertEqual(cached_by_account, self.user_profile)

    def test_str(self):
        """
        Test the `__str__` method.

        Checks that the string representation of the UserProfile instance is correct and robust to missing user or account.
        """
        expected_str = f"UserProfile: {self.user_profile.user.username} (Account: {self.user_profile.account.name})"
        self.assertEqual(str(self.user_profile), expected_str)

    def test_repr(self):
        """
        Test the `__repr__` method.

        Ensures that the repr of the UserProfile instance matches its string representation.
        """
        expected_repr = f"UserProfile: {self.user_profile.user.username} (Account: {self.user_profile.account.name})"
        self.assertEqual(repr(self.user_profile), expected_repr)
