# pylint: disable=wrong-import-position
"""Test Secret Manager."""

import os

import yaml

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.manifest.models.secret.const import MANIFEST_KIND
from smarter.apps.secret.manifest.models.secret.model import SAMSecret
from smarter.apps.secret.manifest.transformers.secret import (
    SecretTransformer,
    SmarterSecretTransformerError,
)
from smarter.apps.secret.models import Secret
from smarter.common.utils import to_snake_case
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.typing import required

HERE = os.path.abspath(os.path.dirname(__file__))
DATA = os.path.join(HERE, "..", "..", "models", "tests", "data")


class TestSmarterSecretTransformer(TestAccountMixin):
    """Test Secret Manager."""

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(DATA, filename)

    def test_manager_01_empty(self):
        """Test that the SecretTransformer cannot be initialized without any secret data."""
        with self.assertRaises(SmarterSecretTransformerError):
            SecretTransformer(user_profile=self.user_profile)

    def test_manager_02_example_manifest(self):
        """Test that the example manifest method returns a dictionary from a call to the SecretTransformer class method."""
        example_manifest = SecretTransformer.example_manifest()
        self.assertIsInstance(example_manifest, dict)

    def test_manager_03_manifest_load(self):
        """Test initialization of the SecretTransformer with a good manifest file."""
        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())

        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertEqual(secret_transformer.name, manifest.metadata.name)
        self.assertEqual(secret_transformer.api_version, manifest.apiVersion)
        self.assertEqual(secret_transformer.kind, MANIFEST_KIND)
        self.assertEqual(secret_transformer.kind, manifest.kind)

        django_model_dict = secret_transformer.manifest_to_django_orm()
        self.assertEqual(secret_transformer.value, "test-password", "Value should match the manifest value")
        self.assertNotEqual(
            secret_transformer.encrypted_value,
            secret_transformer.value,
            "Encrypted value should not be equal to the plain value",
        )
        self.assertEqual(secret_transformer.description, "A secret for testing purposes")
        self.assertIsNone(secret_transformer.last_accessed, "Last accessed should be None")
        self.assertEqual(required(secret_transformer.expires_at, "expires_at").date().isoformat(), "2026-12-31")
        self.assertIsNone(secret_transformer.id, "ID should be None")
        self.assertIsNone(secret_transformer.secret, "Secret should not be set yet")
        self.assertIsNone(secret_transformer.secret_serializer, "Secret serializer should not be set yet")
        self.assertIsInstance(django_model_dict, dict, "django_model_dict should be a dictionary")
        self.assertIsInstance(self.user_profile, UserProfile)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.data, dict, "Secret manager data should be a dictionary")
        self.assertIsInstance(secret_transformer.yaml, str, "Secret manager yaml should exist and be a string")
        try:
            if not isinstance(secret_transformer.yaml, str):
                raise ValueError("YAML should be a string")
            yaml.safe_load(secret_transformer.yaml)
        except yaml.YAMLError as exc:
            self.fail(f"secret_transformer.yaml generated invalid YAML:\n{yaml}\n{exc}")

        self.assertIsInstance(
            secret_transformer.yaml_to_json(secret_transformer.yaml),
            dict,
            "YAML to JSON conversion should return a dictionary",
        )
        self.assertTrue(secret_transformer.is_valid_yaml(secret_transformer.yaml), "YAML should be valid")
        self.assertIsInstance(secret_transformer.to_json(), dict, "to_json should return a dictionary")

    def test_manager_04_create_instance(self):
        """Test creating a Django model instance from the SecretTransformer."""
        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())

        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)

        self.assertTrue(secret_transformer.create())
        self.assertIsNotNone(secret_transformer.secret, "Secret should be set after creation")
        secret = secret_transformer.secret
        assert secret is not None
        secret_manifest = secret_transformer.manifest
        assert secret_manifest is not None
        self.assertIsNotNone(
            required(secret_transformer.secret_serializer, "secret_serializer").data,
            "Secret serializer should be set after creation",
        )
        self.assertEqual(secret_transformer.user_profile, secret.user_profile)

        self.assertEqual(secret.name, secret_transformer.name, "Secret name should match the manifest name")
        self.assertEqual(
            secret.name,
            secret_manifest.metadata.name,
            "Secret name should match the manifest metadata name",
        )
        self.assertEqual(
            secret.get_secret(update_last_accessed=False),
            secret_transformer.value,
            f"Secret value should be {secret_transformer.value}",
        )
        self.assertEqual(
            secret.description,
            secret_transformer.description,
            "Secret description should match the manifest description",
        )
        self.assertEqual(
            secret.description,
            secret_manifest.metadata.description,
            "Secret description should match the manifest metadata description",
        )
        self.assertEqual(
            required(secret.expires_at, "secret.expires_at").date(),
            required(secret_transformer.expires_at, "expires_at").date(),
            "Secret expires_at should match the manifest expires_at",
        )
        self.assertEqual(
            required(secret.expires_at, "secret.expires_at").date(),
            required(secret_manifest.spec.config.expiration_date, "expiration_date").date(),
            "Secret expires_at should match the manifest spec config expiration_date",
        )

    def test_manager_05_initialize(self):
        """Test initializing from manifest for an existing secret."""
        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)

        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)

    def test_manager_06_update(self):
        """Test updating the secret value."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)

        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertTrue(secret_transformer.update())

        self.assertIsNotNone(secret_transformer.secret, "Secret should be set after update")
        secret = secret_transformer.secret
        assert secret is not None
        secret_manifest = secret_transformer.manifest
        assert secret_manifest is not None
        self.assertIsNotNone(
            required(secret_transformer.secret_serializer, "secret_serializer").data,
            "Secret serializer should be set after update",
        )
        self.assertEqual(secret.name, secret_transformer.name, "Secret name should match the manifest name")
        self.assertEqual(
            secret.name,
            secret_manifest.metadata.name,
            "Secret name should match the manifest metadata name",
        )
        self.assertEqual(
            secret.get_secret(update_last_accessed=False),
            secret_transformer.value,
            "Secret value should match the manifest value",
        )
        self.assertEqual(
            secret.get_secret(update_last_accessed=False),
            secret_transformer.value,
            "Secret value should match the manifest value",
        )
        self.assertEqual(
            secret.description,
            secret_transformer.description,
            "Secret description should match the manifest description",
        )
        self.assertEqual(
            secret.description,
            secret_manifest.metadata.description,
            "Secret description should match the manifest metadata description",
        )
        self.assertEqual(
            required(secret.expires_at, "secret.expires_at").date(),
            required(secret_transformer.expires_at, "expires_at").date(),
            "Secret expires_at should match the manifest expires_at",
        )
        self.assertEqual(
            required(secret.expires_at, "secret.expires_at").date(),
            required(secret_manifest.spec.config.expiration_date, "expiration_date").date(),
            "Secret expires_at should match the manifest spec config expiration_date",
        )

    def test_manager_07_update_last_accessed(self):
        """Test updating the last accessed time."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)
        secret = secret_transformer.secret
        assert secret is not None

        # basic test of last_accessed
        last_updated_before = secret.last_accessed
        value = secret.get_secret()
        self.assertIsNotNone(value, "Secret value should not be None")
        self.assertEqual(value, "a-different-test-password")
        last_updated_after = secret.last_accessed
        self.assertNotEqual(last_updated_before, last_updated_after, "Last accessed time should be updated")

        # test with disabled update_last_accessed
        last_updated_before = secret.last_accessed
        secret.get_secret(update_last_accessed=False)
        last_updated_after = secret.last_accessed
        self.assertEqual(last_updated_before, last_updated_after, "Last accessed time should not be updated")

    def test_manager_08_initialize_by_name(self):
        """Test initializing the SecretTransformer with a name."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        secret_transformer.create()

        secret_transformer = SecretTransformer(name=manifest.metadata.name, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertEqual(secret_transformer.name, to_snake_case(manifest.metadata.name))
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)
        secret_transformer.delete()

    def test_manager_09_initialize_by_id(self):
        """Test initializing the SecretTransformer with an ID."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        secret_transformer.create()

        secret_transformer = SecretTransformer(name=manifest.metadata.name, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)
        secret_id = required(secret_transformer.secret, "secret").id

        secret_transformer = SecretTransformer(secret_id=secret_id, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertEqual(required(secret_transformer.secret, "secret").id, secret_id)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)
        secret_transformer.delete()

    def test_manager_10_initialize_by_secret_instance(self):
        """Test initializing the SecretTransformer with a Secret instance."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        secret_transformer.create()

        secret_transformer = SecretTransformer(name=manifest.metadata.name, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        secret = secret_transformer.secret
        self.assertIsInstance(secret, Secret)

        secret_transformer = SecretTransformer(secret=secret, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertEqual(required(secret_transformer.secret, "secret").id, required(secret, "secret").id)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)
        secret_transformer.delete()

    def test_manager_11_initialize_by_secret_serializer(self):
        """Test initializing the SecretTransformer with the json of a Secret that exists, which updates it."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        secret_transformer.create()

        secret_transformer = SecretTransformer(name=manifest.metadata.name, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)
        secret_dict = secret_transformer.to_json()
        self.assertIsInstance(secret_dict, dict, msg="Secret serializer data should be a dictionary:")
        secret_transformer = SecretTransformer(data=secret_dict, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertIsInstance(secret_transformer.secret, Secret)
        self.assertEqual(required(secret_transformer.secret, "secret").id, secret_transformer.id)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        secret_transformer.delete()

    def test_manager_12_initialize_by_different_user_profile(self):
        """Test initializing the SecretTransformer with a different user profile."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        secret_transformer.create()

        # a SecretTransformer finds only the user profile's own Secret of that name, so another
        # user of the account does not find this one.
        other = SecretTransformer(name=manifest.metadata.name, user_profile=self.non_admin_user_profile)
        self.assertIsNone(other.secret)
        self.assertFalse(other.ready)

        secret_transformer.delete()

    def test_manager_13_delete(self):
        """Test deleting the secret."""
        filespec = self.get_data_full_filepath("secret-good-update.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        manifest = SAMSecret(**loader.pydantic_model_dump())
        secret_transformer = SecretTransformer(manifest=manifest, user_profile=self.user_profile)
        secret_transformer.create()

        secret_transformer = SecretTransformer(name=manifest.metadata.name, user_profile=self.user_profile)
        self.assertIsInstance(secret_transformer, SecretTransformer)
        self.assertTrue(secret_transformer.ready, "Secret manager should be ready")
        self.assertIsInstance(secret_transformer.secret, Secret)
        self.assertTrue(secret_transformer.delete())

        self.assertIsNone(secret_transformer.secret, "Secret should be None after deletion")
        self.assertIsNone(secret_transformer.secret_serializer, "Secret serializer should be None after deletion")
        self.assertFalse(secret_transformer.ready, "Secret manager should not be ready after deletion")
        secret_transformer.delete()
