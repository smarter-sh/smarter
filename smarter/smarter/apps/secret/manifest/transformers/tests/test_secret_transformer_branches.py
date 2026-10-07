"""Test the SecretTransformer's initialization options, ORM-backed properties and error branches."""

import copy
from unittest.mock import patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.manifest.models.secret.model import SAMSecret
from smarter.apps.secret.manifest.transformers.secret import (
    SecretTransformer,
    SmarterSecretTransformerError,
)
from smarter.apps.secret.models import Secret
from smarter.lib.manifest.exceptions import SAMValidationError


class TestSecretTransformerBranches(TestAccountMixin):
    """Test the SecretTransformer branches that the manifest-file tests don't reach."""

    @classmethod
    def tearDownClass(cls):
        Secret.objects.filter(user_profile=cls.user_profile, name__startswith="transformer_branches").delete()
        super().tearDownClass()

    def manifest_data(self, name: str) -> dict:
        """Return an example Secret manifest dict, with the given name and tags."""
        data = copy.deepcopy(SecretTransformer.example_manifest())
        data["metadata"]["name"] = name
        data["metadata"]["tags"] = ["alpha", "beta"]
        data["metadata"]["annotations"] = [{"smarter.sh/owner": "tests"}]
        return data

    def create_secret(self, suffix: str) -> SecretTransformer:
        """Create a Secret from a manifest dict, and delete it after the test."""
        name = f"transformer_branches_{suffix}_{self.hash_suffix}"
        transformer = SecretTransformer(user_profile=self.user_profile, data=self.manifest_data(name))
        self.addCleanup(Secret.objects.filter(user_profile=self.user_profile, name=name).delete)
        return transformer

    def test_data_dict_creates_the_secret(self):
        """A manifest dict creates the Secret, with its tags and annotations."""
        transformer = self.create_secret("data")
        secret = Secret.objects.get(user_profile=self.user_profile, name=transformer.name)
        self.assertEqual(transformer.id, secret.id)
        self.assertEqual(transformer.tags, {"alpha", "beta"})
        self.assertEqual(transformer.annotations, [{"smarter.sh/owner": "tests"}])
        self.assertEqual(transformer.version, "0.1.0")
        self.assertIn(transformer.name, str(transformer))
        self.assertEqual(repr(transformer), str(transformer))

    def test_data_dict_of_the_wrong_kind(self):
        """A manifest dict of another kind is rejected."""
        data = self.manifest_data("transformer_branches_wrong_kind")
        data["kind"] = "Plugin"
        with self.assertRaises(SAMValidationError):
            SecretTransformer(user_profile=self.user_profile, data=data)

    def test_incompatible_api_version(self):
        """An unknown apiVersion is rejected, at init and by the setter."""
        with self.assertRaises(SmarterSecretTransformerError):
            SecretTransformer(user_profile=self.user_profile, name="x", api_version="smarter.sh/v0")
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_none")
        with self.assertRaises(SAMValidationError):
            transformer.api_version = "smarter.sh/v0"

    def test_manifest_of_the_wrong_type(self):
        """A manifest that isn't a SAMSecret is rejected, at init and by the manifest property."""
        with self.assertRaises(SAMValidationError):
            SecretTransformer(user_profile=self.user_profile, manifest={"kind": "Secret"})  # type: ignore[arg-type]
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_none")
        transformer._manifest = {"kind": "Secret"}  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError):
            _ = transformer.manifest

    def test_requires_a_user_profile(self):
        """A transformer without a user profile is rejected."""
        with self.assertRaises(SmarterSecretTransformerError):
            SecretTransformer(user_profile=None, name="x")  # type: ignore[arg-type]

    def test_properties_from_the_orm(self):
        """A transformer initialized from a Secret reads every property from the ORM."""
        created = self.create_secret("orm")
        transformer = SecretTransformer(user_profile=self.user_profile, secret_id=created.id)
        self.assertEqual(transformer.value, "test-password")
        self.assertEqual(transformer.encrypted_value, transformer.secret.encrypted_value)
        self.assertEqual(transformer.description, "A secret for testing purposes")
        self.assertIsNotNone(transformer.created_at)
        self.assertIsNotNone(transformer.updated_at)
        self.assertIsNotNone(transformer.expires_at)
        self.assertIsNone(transformer.last_accessed)
        manifest = transformer.manifest
        self.assertIsInstance(manifest, SAMSecret)
        self.assertEqual(manifest.metadata.name, created.name)
        self.assertEqual(manifest.status.accountNumber, self.account.account_number)

    def test_properties_without_a_secret(self):
        """A transformer with only a name has no ORM-backed properties."""
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_missing")
        self.assertIsNone(transformer.value)
        self.assertIsNone(transformer.encrypted_value)
        self.assertIsNone(transformer.description)
        self.assertIsNone(transformer.created_at)
        self.assertIsNone(transformer.updated_at)
        self.assertIsNone(transformer.expires_at)
        self.assertEqual(transformer.version, "1.0.0")
        self.assertEqual(transformer.tags, set())
        self.assertEqual(transformer.annotations, [])
        self.assertIsNone(transformer.manifest_to_django_orm())

    def test_not_ready(self):
        """A transformer that isn't ready has no data and can't refresh, save or delete."""
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_missing")
        self.assertFalse(transformer.ready)
        self.assertIsNone(transformer.data)
        self.assertIsNone(transformer.yaml)
        self.assertIsNone(transformer.to_json())
        self.assertFalse(transformer.refresh())
        self.assertFalse(transformer.save())
        self.assertFalse(transformer.delete())
        self.assertFalse(transformer.create())
        self.assertFalse(transformer.update())

    def test_ready_without_a_user_profile(self):
        """Ready is False once the user profile is gone."""
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_missing")
        transformer._user_profile = None
        self.assertFalse(transformer.ready)
        self.assertIsNone(transformer.secret)

    def test_secret_without_a_name(self):
        """Secret is None when there's no name to look it up by."""
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_missing")
        transformer.name = ""
        self.assertIsNone(transformer.secret)

    def test_id_setter(self):
        """Setting id loads the Secret, clears it on 0, and raises for an unknown pk."""
        created = self.create_secret("id")
        transformer = SecretTransformer(user_profile=self.user_profile, secret_id=created.id)
        self.assertTrue(transformer.refresh())
        transformer.id = 0
        self.assertIsNone(transformer._secret)
        with self.assertRaises(SmarterSecretTransformerError):
            transformer.id = 2**31 - 1

    def test_name_setter_conflicts(self):
        """The name can't be changed away from the manifest's or the Secret's name."""
        created = self.create_secret("name")
        with self.assertRaises(SmarterSecretTransformerError):
            created.name = "transformer_branches_other"
        transformer = SecretTransformer(user_profile=self.user_profile, secret=created.secret)
        transformer._manifest = None
        with self.assertRaises(SmarterSecretTransformerError):
            transformer.name = "transformer_branches_other"
        transformer.name = created.name
        self.assertEqual(transformer.name, created.name)

    def test_secret_setter(self):
        """Setting secret takes its name and user profile."""
        created = self.create_secret("setter")
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_missing")
        transformer._name = None
        transformer.secret = created.secret
        self.assertEqual(transformer.name, created.name)
        self.assertEqual(transformer.user_profile, self.user_profile)

    def test_create_updates_an_existing_secret(self):
        """Create() for a Secret that already exists updates it."""
        created = self.create_secret("recreate")
        data = self.manifest_data(created.name)
        data["metadata"]["description"] = "updated description"
        transformer = SecretTransformer(user_profile=self.user_profile, data=data)
        self.assertEqual(transformer.id, created.id)
        self.assertEqual(Secret.objects.get(pk=created.id).description, "updated description")

    def test_create_without_orm_data(self):
        """Create() raises when the manifest can't be mapped to the ORM."""
        created = self.create_secret("orm_data")
        created._secret = None
        created._name = None
        with patch.object(SecretTransformer, "secret", None):
            with patch.object(SecretTransformer, "manifest_to_django_orm", return_value=None):
                with self.assertRaises(SmarterSecretTransformerError):
                    created.create()

    def test_update_without_orm_data(self):
        """Update() returns False when the manifest can't be mapped to the ORM."""
        created = self.create_secret("update")
        with patch.object(SecretTransformer, "manifest_to_django_orm", return_value=None):
            self.assertFalse(created.update())

    def test_save_and_delete(self):
        """Save() persists the Secret and delete() removes it."""
        created = self.create_secret("delete")
        secret_id = created.id
        self.assertTrue(created.save())
        self.assertTrue(created.delete())
        self.assertFalse(Secret.objects.filter(pk=secret_id).exists())

    def test_to_json_rejects_an_unknown_version(self):
        """To_json() only knows v1."""
        created = self.create_secret("json")
        self.assertIsInstance(created.to_json(), dict)
        with self.assertRaises(SmarterSecretTransformerError):
            created.to_json(version="v2")

    def test_yaml_to_json_rejects_invalid_yaml(self):
        """Yaml_to_json() raises for invalid YAML."""
        transformer = SecretTransformer(user_profile=self.user_profile, name="transformer_branches_missing")
        self.assertEqual(transformer.yaml_to_json("a: 1"), {"a": 1})
        self.assertFalse(transformer.is_valid_yaml("a: [1"))
        with self.assertRaises(SmarterSecretTransformerError):
            transformer.yaml_to_json("a: [1")
