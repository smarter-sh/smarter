# pylint: disable=wrong-import-position
"""Test SmarterQuerySetWithPermissions."""

# our stuff
import logging

from django.test import Client

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.secret.models import Secret, SmarterQuerySetWithPermissions
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)


class TestSmarterQuerySetWithPermissions(TestAccountMixin):
    """Test SmarterQuerySetWithPermissions model"""

    logger_prefix = formatted_text(f"{__name__}.TestSmarterQuerySetWithPermissions()")

    @classmethod
    def setUpClass(cls):
        """
        Ensure that the Secret model has some data to query against.
        """
        super().setUpClass()

        cls.unrelated_account_admin, cls.unrelated_account, cls.unrelated_account_user_profile = admin_user_factory()
        cls.unrelated_non_admin_user, _, cls.unrelated_non_admin_user_profile = mortal_user_factory(
            account=cls.unrelated_account
        )

        cls.account1_secret1 = Secret.objects.create(
            name="Secret 1",
            encrypted_value=Secret.encrypt("supersecret1"),
            user_profile=cls.user_profile,
        )
        cls.account1_secret2 = Secret.objects.create(
            name="Secret 2",
            encrypted_value=Secret.encrypt("supersecret2"),
            user_profile=cls.user_profile,
        )

        cls.account2_secret1 = Secret.objects.create(
            name="Secret 3",
            encrypted_value=Secret.encrypt("supersecret3"),
            user_profile=cls.unrelated_non_admin_user_profile,
        )

        cls.account2_secret2 = Secret.objects.create(
            name="Secret 4",
            encrypted_value=Secret.encrypt("supersecret4"),
            user_profile=cls.unrelated_non_admin_user_profile,
        )
        cls.test_secrets = [cls.account1_secret1, cls.account1_secret2, cls.account2_secret1, cls.account2_secret2]

    @classmethod
    def tearDownClass(cls):
        """
        Clean up the accounts and users created for this test case.
        """
        try:
            factory_account_teardown(
                user=cls.unrelated_account_admin,
                account=cls.unrelated_account,
                user_profile=cls.unrelated_account_user_profile,
            )
        # pylint: disable=W0718
        except Exception:
            pass
        try:
            factory_account_teardown(
                user=cls.unrelated_non_admin_user,
                account=cls.unrelated_account,
                user_profile=cls.unrelated_non_admin_user_profile,
            )
        # pylint: disable=W0718
        except Exception:
            pass

        try:
            for secret in cls.test_secrets:
                secret.delete()
        # pylint: disable=W0718
        except Exception:
            pass
        finally:
            super().tearDownClass()

    def setUp(self):
        """
        Set up the test case.
        - Our admin user will the be the authenticated user for all tests.
        - The non_admin_user will be the unauthenticated user for all tests.

        """
        super().setUp()
        client = Client()
        client.force_login(self.admin_user)
        client.force_login(self.unrelated_non_admin_user)
        self.assertTrue(self.admin_user.is_authenticated)
        self.assertTrue(self.unrelated_non_admin_user.is_authenticated)

        self.assertTrue(self.admin_user.is_superuser)
        self.assertFalse(self.unrelated_non_admin_user.is_superuser)
        self.assertFalse(self.unrelated_non_admin_user.is_staff)

        # Create a mock queryset. We can use any model that inherits from MetaDataWithOwnershipModel,
        # and Secret is the most convenient.
        self.queryset = SmarterQuerySetWithPermissions(model=Secret, using="default")
        self.control_count = self.queryset.count()  # This should be 4, since we created four secrets in setUpClass()

    def test_with_read_permission_for_non_user(self):
        """
        Test that an unauthenticated user has no read permissions.
        """
        not_a_user = object()
        result = self.queryset.with_read_permission_for(not_a_user)  # type: ignore
        self.assertEqual(result.count(), 0)

    def test_with_read_permission_for_unauthenticated_user(self):
        """
        Test that an unauthenticated user has no read permissions.
        """

        result = self.queryset.with_read_permission_for(object())  # type: ignore
        self.assertEqual(result.count(), 0)

    def test_with_read_permission_for_superuser(self):
        """
        Test that a superuser has read permissions for all objects.
        """

        result = self.queryset.with_read_permission_for(self.admin_user)
        self.assertEqual(result.count(), self.control_count)

    def test_with_read_permission_for_regular_unrelated_user(self):
        """
        Test that a regular user has read permissions only for their own objects.
        """
        smarter_admin_read_count = self.queryset.with_read_permission_for(smarter_cached_objects.smarter_admin).count()
        result = self.queryset.with_read_permission_for(self.unrelated_non_admin_user)
        self.assertEqual(smarter_admin_read_count - result.count(), 2)

        ownership_set = [
            smarter_cached_objects.smarter_admin_user_profile,
            self.unrelated_non_admin_user_profile,
            self.user_profile,
        ]
        # Assert that the secrets returned are the ones created by the unrelated non-admin user
        for secret in result:
            self.assertIn(secret.user_profile, ownership_set)

    def test_with_read_permission_for_staff_user(self):
        """
        Test that a staff user has read permissions for all objects in the account.
        """

        logger.debug(
            "%s.test_with_read_permission_for_staff_user() starting test with unrelated_non_admin_user %s",
            self.logger_prefix,
            self.unrelated_non_admin_user,
        )

        # temporarily demote the admin user to staff to test this case
        logger.debug(
            "%s.test_with_read_permission_for_staff_user() demoting admin user to staff",
            self.logger_prefix,
        )
        self.admin_user.is_superuser = False
        self.admin_user.is_staff = True
        self.admin_user.save()

        self.assertFalse(self.admin_user.is_superuser)
        self.assertTrue(self.admin_user.is_staff)

        try:

            smarter_admin_read_count = self.queryset.with_read_permission_for(
                smarter_cached_objects.smarter_admin
            ).count()
            account_admin_read_count = self.queryset.with_read_permission_for(self.admin_user).count()
            self.assertEqual(smarter_admin_read_count - account_admin_read_count, 2)
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"with_read_permission_for() raised an exception for staff user: {e}")
        finally:
            logger.debug(
                "%s.test_with_read_permission_for_staff_user() restoring admin user's superuser status",
                self.logger_prefix,
            )
            # restore the admin user's superuser status
            self.admin_user.is_superuser = True
            self.admin_user.is_staff = False
            self.admin_user.save()

    def test_with_ownership_permission_for_not_user_instance(self):
        """
        Test that an object that is not a user has no ownership permissions.
        """
        not_a_user = object()
        result = self.queryset.with_ownership_permission_for(not_a_user)  # type: ignore
        self.assertEqual(result.count(), 0)

    def test_with_ownership_permission_for_unauthenticated_user(self):
        """
        Test that an unauthenticated user has no ownership permissions.
        """
        result = self.queryset.with_ownership_permission_for(object())  # type: ignore
        self.assertEqual(result.count(), 0)

    def test_with_ownership_permission_for_superuser(self):
        """
        Test that a superuser has ownership permissions for all objects.
        """

        result = self.queryset.with_ownership_permission_for(self.admin_user)
        self.assertEqual(result.count(), self.control_count)

    def test_with_ownership_permission_for_staff_user(self):
        """
        Test that a staff user has ownership permissions for all objects in the account.
        """

        # temporarily demote the admin user to staff to test this case
        self.admin_user.is_superuser = False
        self.admin_user.is_staff = True
        self.admin_user.save()

        try:
            result = self.queryset.with_ownership_permission_for(self.admin_user)
            self.assertEqual(result.count(), 2)

        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"with_ownership_permission_for() raised an exception for staff user: {e}")
        finally:
            # restore the admin user's superuser status
            self.admin_user.is_superuser = True
            self.admin_user.is_staff = False
            self.admin_user.save()

    def test_with_ownership_permission_for_regular_user(self):
        """
        Test that a regular user has ownership permissions only for their own objects.
        """

        logger.debug(
            "%s.test_with_ownership_permission_for_regular_user() starting test with unrelated_non_admin_user %s",
            self.logger_prefix,
            self.unrelated_non_admin_user,
        )

        result = self.queryset.with_ownership_permission_for(self.unrelated_non_admin_user)
        self.assertEqual(result.count(), 2)

        # Assert that the secrets returned are the ones created by the unrelated non-admin user
        for secret in result:
            self.assertEqual(secret.user_profile, self.unrelated_non_admin_user_profile)
