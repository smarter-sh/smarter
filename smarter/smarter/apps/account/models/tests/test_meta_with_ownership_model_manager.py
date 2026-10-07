# pylint: disable=wrong-import-position
"""Test RBAC methods from MetaDataWithOwnershipModelManager class."""

from smarter.apps.account.tests.factories import (
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.secret.models import Secret
from smarter.lib import logging

logger = logging.getLogger(__name__)


class TestMetaDataWithOwnershipModelManager(TestAccountMixin):
    """
    Test RBAC methods from MetaDataWithOwnershipModelManager class.
    Test 4 kinds of users from 3 different accounts:

    1. Smarter admin user (superuser, staff, belongs to Smarter account)
    2. Admin user (staff, belongs to Account 1)
    3. Non-admin user (does not have staff status, belongs to Account 1)
    4. Other non-admin user (does not have staff status, belongs to Account 2)
    """

    logger_prefix = logging.formatted_text(f"{__name__}.TestMetaDataWithOwnershipModelManager()")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # we want our test admin user to only have staff status, but not superuser status,
        # so that we can test the RBAC methods for a user with elevated permissions but not full superuser access
        cls.admin_user.is_superuser = False
        cls.admin_user.save()

        cls.other_non_admin_user, cls.other_account, cls.other_non_admin_user_profile = mortal_user_factory()

        cls.secret_non_admin_user = Secret.objects.create(
            name="Test Secret Non-Admin User Account 1",
            encrypted_value=Secret.encrypt("supersecret1"),
            user_profile=cls.non_admin_user_profile,
        )
        cls.secret_other_non_admin_user = Secret.objects.create(
            name="Test Secret Other Non-Admin User Account 2",
            encrypted_value=Secret.encrypt("supersecret3"),
            user_profile=cls.other_non_admin_user_profile,
        )
        cls.secret_admin_user = Secret.objects.create(
            name="Test Secret Admin User Account 1",
            encrypted_value=Secret.encrypt("supersecret2"),
            user_profile=cls.user_profile,
        )
        cls.secret_smarter_admin_user = Secret.objects.create(
            name="Test Secret Smarter Admin User Smarter Account",
            encrypted_value=Secret.encrypt("supersecret4"),
            user_profile=smarter_cached_objects.smarter_admin_user_profile,
        )
        cls.secrets = [
            cls.secret_non_admin_user,
            cls.secret_other_non_admin_user,
            cls.secret_admin_user,
            cls.secret_smarter_admin_user,
        ]
        logger.debug("%s Created secrets for testing: %s", cls.logger_prefix, [secret.name for secret in cls.secrets])

    @classmethod
    def tearDownClass(cls):
        try:
            for secret in cls.secrets:
                secret.delete()
        # pylint: disable=W0718
        except Exception:
            logger.exception("%s Failed to delete secrets during tearDownClass.", cls.logger_prefix)
        finally:
            factory_account_teardown(
                user=cls.other_non_admin_user, account=cls.other_account, user_profile=cls.other_non_admin_user_profile
            )
            super().tearDownClass()

    def test_with_read_permission_for_smarter_admin_user(self):
        """Test that with_read_permission_for() returns the correct secrets for the smarter admin user."""

        secrets = Secret.objects.with_read_permission_for(smarter_cached_objects.smarter_admin_user_profile.user)  # type: ignore
        # yes
        self.assertIn(
            self.secret_smarter_admin_user, secrets, "Smarter admin user should have access to their own secret."
        )
        self.assertIn(self.secret_admin_user, secrets, "Smarter admin user should have access to admin user's secret.")
        self.assertIn(
            self.secret_non_admin_user, secrets, "Smarter admin user should have access to non-admin user's secret."
        )
        self.assertIn(
            self.secret_other_non_admin_user,
            secrets,
            "Smarter admin user should have access to other non-admin user's secret.",
        )

    def test_with_ownership_permission_for_smarter_admin_user(self):
        """Test that with_ownership_permission_for() returns the correct secrets for the smarter admin user."""

        secrets = Secret.objects.with_ownership_permission_for(smarter_cached_objects.smarter_admin_user_profile.user)  # type: ignore
        # yes
        self.assertIn(
            self.secret_smarter_admin_user,
            secrets,
            "Smarter admin user should have ownership access to their own secret.",
        )
        self.assertIn(
            self.secret_admin_user, secrets, "Smarter admin user should have ownership access to admin user's secret."
        )
        self.assertIn(
            self.secret_non_admin_user,
            secrets,
            "Smarter admin user should have ownership access to non-admin user's secret.",
        )
        self.assertIn(
            self.secret_other_non_admin_user,
            secrets,
            "Smarter admin user should have ownership access to other non-admin user's secret.",
        )

    def test_with_read_permission_for_admin_user(self):
        """Test that with_read_permission_for() returns the correct secrets for the admin user."""

        secrets = Secret.objects.with_read_permission_for(self.admin_user)
        # yes
        self.assertIn(self.secret_admin_user, secrets, "Admin user should have access to their own secret.")
        self.assertIn(self.secret_non_admin_user, secrets, "Admin user should have access to non-admin user's secret.")
        self.assertIn(
            self.secret_smarter_admin_user, secrets, "Admin user should have access to smarter admin user's secret."
        )

        # no. wrong account
        self.assertNotIn(
            self.secret_other_non_admin_user, secrets, "Admin user should have access to other non-admin user's secret."
        )

    def test_with_ownership_permission_for_admin_user(self):
        """
        Test that with_ownership_permission_for() returns the correct secrets for the admin user.
        """

        secrets = Secret.objects.with_ownership_permission_for(self.admin_user)
        # yes
        self.assertIn(self.secret_admin_user, secrets, "Admin user should have ownership access to their own secret.")
        self.assertIn(
            self.secret_non_admin_user, secrets, "Admin user should have ownership access to non-admin user's secret."
        )

        # no. wrong account
        self.assertNotIn(
            self.secret_smarter_admin_user,
            secrets,
            "Admin user should not have ownership access to smarter admin user's secret.",
        )
        self.assertNotIn(
            self.secret_other_non_admin_user,
            secrets,
            "Admin user should not have ownership access to other non-admin user's secret.",
        )

    def test_with_read_permission_for_non_admin_user(self):
        """Test that with_read_permission_for() returns the correct secrets for the non-admin user."""

        secrets = Secret.objects.with_read_permission_for(self.non_admin_user)
        # yes
        self.assertIn(self.secret_non_admin_user, secrets, "Non-admin user should have access to their own secret.")
        self.assertIn(self.secret_admin_user, secrets, "Non-admin user should have access to admin user's secret.")
        self.assertIn(
            self.secret_smarter_admin_user, secrets, "Non-admin user should have access to smarter admin user's secret."
        )

        # no. wrong account
        self.assertNotIn(
            self.secret_other_non_admin_user,
            secrets,
            "Non-admin user should not have access to other non-admin user's secret.",
        )

    def test_with_ownership_permission_for_non_admin_user(self):
        """Test that with_ownership_permission_for() returns the correct secrets for the non-admin user."""

        secrets = Secret.objects.with_ownership_permission_for(self.non_admin_user)
        # yes
        self.assertIn(
            self.secret_non_admin_user, secrets, "Non-admin user should have ownership access to their own secret."
        )

        # no. not the owner
        self.assertNotIn(
            self.secret_admin_user, secrets, "Non-admin user should not have ownership access to admin user's secret."
        )
        self.assertNotIn(
            self.secret_smarter_admin_user,
            secrets,
            "Non-admin user should not have ownership access to smarter admin user's secret.",
        )
        self.assertNotIn(
            self.secret_other_non_admin_user,
            secrets,
            "Non-admin user should not have ownership access to other non-admin user's secret.",
        )

    def test_with_read_permission_for_other_non_admin_user(self):
        """Test that with_read_permission_for() returns the correct secrets for the othernon-admin user."""

        secrets = Secret.objects.with_read_permission_for(self.other_non_admin_user)
        # yes
        self.assertIn(
            self.secret_other_non_admin_user, secrets, "Other non-admin user should have access to their own secret."
        )
        self.assertIn(
            self.secret_smarter_admin_user,
            secrets,
            "Other non-admin user should have access to smarter admin user's secret.",
        )

        # no. wrong account
        self.assertNotIn(
            self.secret_admin_user, secrets, "Other non-admin user should not have access to admin user's secret."
        )
        self.assertNotIn(
            self.secret_non_admin_user,
            secrets,
            "Other non-admin user should not have access to non-admin user's secret.",
        )

    def test_with_ownership_permission_for_other_non_admin_user(self):
        """Test that with_ownership_permission_for() returns the correct secrets for the other non-admin user."""

        secrets = Secret.objects.with_ownership_permission_for(self.other_non_admin_user)
        # yes
        self.assertIn(
            self.secret_other_non_admin_user,
            secrets,
            "Other non-admin user should have ownership access to their own secret.",
        )

        # no. not the owner
        self.assertNotIn(
            self.secret_admin_user,
            secrets,
            "Other non-admin user should not have ownership access to admin user's secret.",
        )
        self.assertNotIn(
            self.secret_non_admin_user,
            secrets,
            "Other non-admin user should not have ownership access to non-admin user's secret.",
        )
        self.assertNotIn(
            self.secret_smarter_admin_user,
            secrets,
            "Other non-admin user should not have ownership access to smarter admin user's secret.",
        )
