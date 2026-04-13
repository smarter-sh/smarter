# pylint: disable=wrong-import-position
"""Test MetaDataWithOwnershipModel model."""

# our stuff
import logging

from smarter.apps.account.models import Secret
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)


class TestMetaDataWithOwnershipModel(TestAccountMixin):
    """Test MetaDataWithOwnershipModel model"""

    logger_prefix = formatted_text(f"{__name__}.TestMetaDataWithOwnershipModel()")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secret1 = Secret.objects.create(
            name="Test Secret 1",
            encrypted_value=Secret.encrypt("supersecret1"),
            user_profile=cls.user_profile,
        )
        cls.secret2 = Secret.objects.create(
            name="Test Secret 2",
            encrypted_value=Secret.encrypt("supersecret2"),
            user_profile=cls.user_profile,
        )
        cls.secrets = [cls.secret1, cls.secret2]
        logger.debug("%s Created secrets for testing: %s", cls.logger_prefix, [secret.name for secret in cls.secrets])

    @classmethod
    def tearDownClass(cls):
        try:
            for secret in cls.secrets:
                logger.debug("%s Deleting secret: %s", cls.logger_prefix, secret.name)
                secret.delete()
        # pylint: disable=W0718
        except Exception:
            logger.exception("%s Failed to delete secrets during tearDownClass.", cls.logger_prefix)
        finally:
            super().tearDownClass()

    def test_get_cached_object_by_pk(self):
        """
        Test get_cached_object retrieves an object by primary key with caching.
        """

        secret = Secret.get_cached_object(pk=self.secret1.pk, invalidate=True)
        self.assertEqual(secret, self.secret1)

        # Test that the cached object is correctly retrieved again without invalidation
        secret = Secret.get_cached_object(pk=self.secret1.pk)
        self.assertEqual(secret, self.secret1)

    def test_get_cached_object_by_name_and_user_profile(self):
        """
        Test get_cached_object retrieves an object by name and user_profile with caching.
        """

        secret = Secret.get_cached_object(name=self.secret1.name, user_profile=self.user_profile, invalidate=True)
        self.assertIsInstance(secret, Secret)
        self.assertEqual(secret, self.secret1)

        # Test that the cached object is correctly retrieved again without invalidation
        secret = Secret.get_cached_object(name=self.secret1.name, user_profile=self.user_profile)
        self.assertEqual(secret, self.secret1)

    def test_get_cached_object_by_name_and_account(self):
        """
        Test get_cached_object retrieves an object by name and account with caching.
        """

        secret = Secret.get_cached_object(name=self.secret1.name, account=self.account, invalidate=True)
        self.assertIsInstance(secret, Secret)
        self.assertEqual(secret, self.secret1)

        # Test that the cached object is correctly retrieved again without invalidation
        secret = Secret.get_cached_object(name=self.secret1.name, account=self.account)
        self.assertEqual(secret, self.secret1)

    def test_get_cached_object_invalidate_cache(self):
        """
        Test that cache invalidation works as expected in get_cached_object.
        """

        # baseline
        secret = Secret.get_cached_object(pk=self.secret1.pk, invalidate=True)
        self.assertEqual(secret, self.secret1)

        # update the secret and check that the cache is invalidated and updated correctly
        if not isinstance(secret, Secret):
            self.fail(
                f"{self.logger_prefix}.test_get_cached_object_invalidate_cache() - Expected a Secret instance, got {type(secret)}"
            )
        secret.name = "Updated Secret Name"

        # save the secret, which should trigger cache invalidation for this object.
        secret.save()

        # first, verify that our data was persisted.
        self.assertEqual(secret.name, "Updated Secret Name")

        # now, retrieve the secret again using get_cached_object without invalidation.
        # This should return the updated secret, not the old cached version.
        secret = Secret.get_cached_object(pk=self.secret1.pk)
        if not isinstance(secret, Secret):
            self.fail(
                f"{self.logger_prefix}.test_get_cached_object_invalidate_cache() - Expected a Secret instance after update, got {type(secret)}"
            )
        self.assertEqual(secret.name, "Updated Secret Name")
