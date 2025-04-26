# pylint: disable=wrong-import-position
"""Test Secret Manager."""

import json
import logging
import os
import unittest

import yaml

from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.apps.account.models import Secret, UserProfile
from smarter.apps.account.secret import SecretManager, SmarterSecretManagerError
from smarter.lib.manifest.loader import SAMLoader

from .factories import admin_user_factory, admin_user_teardown, mortal_user_factory


HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


class TestSmarterSecretManager(unittest.TestCase):
    """Test Secret Manager."""

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(HERE, "data", filename)

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with a single account, and admin and non-admin users.
        using the class setup so that we retain the same user_profile for each test,
        which is needed so that the django Secret model can be queried.
        """
        cls.admin_user, cls.account, cls.user_profile = admin_user_factory()
        cls.non_admin_user, _, cls.non_admin_user_profile = mortal_user_factory(account=cls.account)

    @classmethod
    def tearDownClass(cls):
        admin_user_teardown(user=cls.admin_user, account=None, user_profile=cls.user_profile)
        admin_user_teardown(user=cls.non_admin_user, account=cls.account, user_profile=cls.non_admin_user_profile)

    def test_manager_01_empty(self):
        """
        Test that the SecretManager can be initialized without any secret data.
        """
        logger.info("test_manager_01_empty()")
        with self.assertRaises(SmarterSecretManagerError):
            SecretManager(self.user_profile)

    def test_manager_02_example_manifest(self):
        """
        Test that the example manifest method returns a dictionary
        from a call to the SecretManager class method.
        """
        logger.info("test_manager_02_example_manifest()")
        example_manifest = SecretManager.example_manifest()
        self.assertIsInstance(example_manifest, dict)

    def test_manager_03_manifest_load(self):
        """
        Test initialization of the SecretManager with a good manifest file.
        """
        logger.info("test_manager_03_manifest_load()")

        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        manifest = SAMSecret(**loader.pydantic_model_dump())

        secret_manager = SecretManager(manifest=manifest, user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertEqual(secret_manager.name, manifest.metadata.name)
        self.assertEqual(secret_manager.api_version, manifest.apiVersion)
        self.assertEqual(secret_manager.kind, MANIFEST_KIND)
        self.assertEqual(secret_manager.kind, manifest.kind)

        django_model_dict = secret_manager.secret_django_model
        self.assertEqual(secret_manager.value, "test-password", "Value should match the manifest value")
        self.assertNotEqual(
            secret_manager.encrypted_value,
            secret_manager.value,
            "Encrypted value should not be equal to the plain value",
        )
        self.assertEqual(secret_manager.description, "A secret for testing purposes")
        self.assertIsNone(secret_manager.last_accessed, "Last accessed should be None")
        self.assertEqual(secret_manager.expires_at, "2026-12-31")
        self.assertIsNone(secret_manager.id, "ID should be None")
        self.assertIsNone(secret_manager.secret, "Secret should not be set yet")
        self.assertIsNone(secret_manager.secret_serializer, "Secret serializer should not be set yet")
        self.assertIsInstance(django_model_dict, dict, "django_model_dict should be a dictionary")
        self.assertIsInstance(self.user_profile, UserProfile)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.data, dict, "Secret manager data should be a dictionary")
        self.assertIsInstance(secret_manager.yaml, str, "Secret manager yaml should exist and be a string")
        try:
            yaml.safe_load(secret_manager.yaml)
        except yaml.YAMLError as exc:
            self.fail(f"secret_manager.yaml generated invalid YAML:\n{yaml}\n{exc}")

        self.assertIsInstance(
            secret_manager.yaml_to_json(secret_manager.yaml), dict, "YAML to JSON conversion should return a dictionary"
        )
        self.assertTrue(secret_manager.is_valid_yaml(secret_manager.yaml), "YAML should be valid")
        self.assertIsInstance(secret_manager.to_json(), dict, "to_json should return a dictionary")

    def test_manager_04_create_instance(self):
        """
        Test creating a Django model instance from the SecretManager.
        """
        logger.info("test_manager_04_create_instance()")
        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        manifest = SAMSecret(**loader.pydantic_model_dump())

        secret_manager = SecretManager(manifest=manifest, user_profile=self.user_profile)

        self.assertTrue(secret_manager.create())
        self.assertIsNotNone(secret_manager.secret, "Secret should be set after creation")
        self.assertIsNotNone(secret_manager.secret_serializer.data, "Secret serializer should be set after creation")
        self.assertEqual(secret_manager.user_profile, secret_manager.secret.user_profile)

        self.assertEqual(secret_manager.secret.name, secret_manager.name, "Secret name should match the manifest name")
        self.assertEqual(
            secret_manager.secret.name,
            secret_manager.manifest.metadata.name,
            "Secret name should match the manifest metadata name",
        )
        self.assertEqual(
            secret_manager.secret.get_secret(update_last_accessed=False),
            secret_manager.value,
            f"Secret value should be {secret_manager.value}",
        )
        self.assertEqual(
            secret_manager.secret.description,
            secret_manager.description,
            "Secret description should match the manifest description",
        )
        self.assertEqual(
            secret_manager.secret.description,
            secret_manager.manifest.metadata.description,
            "Secret description should match the manifest metadata description",
        )
        self.assertEqual(
            secret_manager.secret.expires_at.date().isoformat(),
            secret_manager.expires_at,
            "Secret expires_at should match the manifest expires_at",
        )
        self.assertEqual(
            secret_manager.secret.expires_at.date(),
            secret_manager.manifest.spec.config.expirationDate,
            "Secret expires_at should match the manifest spec config expirationDate",
        )

    def test_manager_05_initialize(self):
        """
        Test initializing from manifest for an existing secret.
        """
        logger.info("test_manager_05_initialize()")
        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_manager = SecretManager(manifest=manifest, user_profile=self.user_profile)

        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)

    def test_manager_06_update(self):
        """
        Test updating the secret value.
        """
        logger.info("test_manager_06_update()")
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_manager = SecretManager(manifest=manifest, user_profile=self.user_profile)

        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertTrue(secret_manager.update())

        self.assertIsNotNone(secret_manager.secret, "Secret should be set after update")
        self.assertIsNotNone(secret_manager.secret_serializer.data, "Secret serializer should be set after update")
        self.assertEqual(secret_manager.secret.name, secret_manager.name, "Secret name should match the manifest name")
        self.assertEqual(
            secret_manager.secret.name,
            secret_manager.manifest.metadata.name,
            "Secret name should match the manifest metadata name",
        )
        self.assertEqual(
            secret_manager.secret.get_secret(update_last_accessed=False),
            secret_manager.value,
            "Secret value should match the manifest value",
        )
        self.assertEqual(
            secret_manager.secret.get_secret(update_last_accessed=False),
            secret_manager.value,
            "Secret value should match the manifest value",
        )
        self.assertEqual(
            secret_manager.secret.description,
            secret_manager.description,
            "Secret description should match the manifest description",
        )
        self.assertEqual(
            secret_manager.secret.description,
            secret_manager.manifest.metadata.description,
            "Secret description should match the manifest metadata description",
        )
        self.assertEqual(
            secret_manager.secret.expires_at.date().isoformat(),
            secret_manager.expires_at,
            "Secret expires_at should match the manifest expires_at",
        )
        self.assertEqual(
            secret_manager.secret.expires_at.date(),
            secret_manager.manifest.spec.config.expirationDate,
            "Secret expires_at should match the manifest spec config expirationDate",
        )

    def test_manager_07_update_last_accessed(self):
        """
        Test updating the last accessed time.
        """
        logger.info("test_manager_07_update_last_accessed()")
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_manager = SecretManager(manifest=manifest, user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)

        # basic test of last_accessed
        last_updated_before = secret_manager.secret.last_accessed
        value = secret_manager.secret.get_secret()
        self.assertIsNotNone(value, "Secret value should not be None")
        self.assertEqual(value, "a-different-test-password")
        last_updated_after = secret_manager.secret.last_accessed
        self.assertNotEqual(last_updated_before, last_updated_after, "Last accessed time should be updated")

        # test with disabled update_last_accessed
        last_updated_before = secret_manager.secret.last_accessed
        secret_manager.secret.get_secret(update_last_accessed=False)
        last_updated_after = secret_manager.secret.last_accessed
        self.assertEqual(last_updated_before, last_updated_after, "Last accessed time should not be updated")

    def test_manager_08_initialze_by_name(self):
        """
        Test initializing the SecretManager with a name.
        """
        logger.info("test_manager_08_initialze_by_name()")

        secret_manager = SecretManager(name="TestSecret", user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertEqual(secret_manager.name, "TestSecret")
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)

    def test_manager_09_initialize_by_id(self):
        """
        Test initializing the SecretManager with an ID.
        """
        logger.info("test_manager_09_initialize_by_id()")
        secret_manager = SecretManager(name="TestSecret", user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)
        secret_id = secret_manager.secret.id

        secret_manager = SecretManager(secret_id=secret_id, user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertEqual(secret_manager.secret.id, secret_id)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)

    def test_manager_10_initialize_by_secret_instance(self):
        """
        Test initializing the SecretManager with a Secret instance.
        """
        logger.info("test_manager_10_initialize_by_secret_instance()")
        secret_manager = SecretManager(name="TestSecret", user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        secret = secret_manager.secret
        self.assertIsInstance(secret, Secret)

        secret_manager = SecretManager(secret=secret, user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertEqual(secret_manager.secret.id, secret.id)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)

    def test_manager_11_initialize_by_secret_serializer(self):
        """
        Test initializing the SecretManager with a Secret serializer.
        """
        logger.info("test_manager_11_initialize_by_secret_serializer()")
        secret_manager = SecretManager(name="TestSecret", user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)
        secret_dict = secret_manager.to_json()
        self.assertIsInstance(secret_dict, dict, msg="Secret serializer data should be a dictionary:")
        logger.info(
            "test_manager_11_initialize_by_secret_serializer() secret_dict: %s", json.dumps(secret_dict, indent=4)
        )
        secret_manager = SecretManager(data=secret_dict, user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertIsInstance(secret_manager.secret, Secret)
        self.assertEqual(secret_manager.secret.id, secret_manager.id)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")

    def test_manager_12_initialize_by_different_user_profile(self):
        """
        Test initializing the SecretManager with a different user profile.
        """
        logger.info("test_manager_12_initialize_by_different_user_profile()")
        secret_manager = SecretManager(name="TestSecret", user_profile=self.non_admin_user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertFalse(secret_manager.ready, "Secret manager should not be ready")
        self.assertIsNone(secret_manager.secret, "Secret should not be set")

    def test_manager_13_delete(self):
        """
        Test deleting the secret.
        """
        logger.info("test_manager_13_delete()")
        secret_manager = SecretManager(name="TestSecret", user_profile=self.user_profile)
        self.assertIsInstance(secret_manager, SecretManager)
        self.assertTrue(secret_manager.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_manager.secret, Secret)
        self.assertTrue(secret_manager.delete())

        self.assertIsNone(secret_manager.secret, "Secret should be None after deletion")
        self.assertIsNone(secret_manager.secret_serializer, "Secret serializer should be None after deletion")
        self.assertFalse(secret_manager.ready, "Secret manager should not be ready after deletion")
