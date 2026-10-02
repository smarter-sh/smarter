"""Test the built-in Vectorstores: :mod:`smarter.apps.vectorstore.builtins`."""

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.models import ApiConnection
from smarter.apps.vectorstore.builtins import (
    add_builtin_vectorstores,
    builtin_manifest_files,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.model import SAMVectorstore
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.loader import SAMLoader

from .base_classes import VectorstoreTestBase


class TestBuiltinVectorstores(VectorstoreTestBase):
    """Test that the built-in manifests are valid, and are applied for a user, but not deployed."""

    def test_manifests(self):
        """Test that every built-in manifest is valid, and their names are unique."""
        files = builtin_manifest_files()
        self.assertGreaterEqual(len(files), 4)
        names = [SAMVectorstore(**get_readonly_yaml_file(f)).metadata.name for f in files]
        self.assertEqual(len(names), len(set(names)))
        backends = {SAMVectorstore(**get_readonly_yaml_file(f)).spec.backend for f in files}
        self.assertEqual(backends, {"qdrant", "pinecone"})

    def write_manifests(self, path: str) -> None:
        """The built-in manifests, with the test's Provider, and with the test's suffix in their names."""
        # pylint: disable=import-outside-toplevel
        import os

        import yaml

        for filename in builtin_manifest_files():
            loader = SAMLoader(file_path=filename)
            manifest = loader.json_data
            manifest["metadata"]["name"] += f"_{self.hash_suffix}"
            manifest["spec"]["embeddings"]["provider"] = self.provider.name
            with open(os.path.join(path, os.path.basename(filename)), "w", encoding="utf-8") as f:
                yaml.safe_dump(manifest, f)

    def test_add_builtin_vectorstores(self):
        """Test that the manifests are applied, not deployed, and those without their ApiConnection are skipped."""
        # pylint: disable=import-outside-toplevel
        import tempfile

        ApiConnection.objects.create(
            name="pinecone",
            user_profile=self.user_profile,
            kind=SAMKinds.API_CONNECTION.value,
            base_url="https://api.pinecone.io",
            api_key=self.secret,
            auth_method="token",
        )
        self.addCleanup(ApiConnection.objects.filter(name="pinecone", user_profile=self.user_profile).delete)
        with tempfile.TemporaryDirectory() as path:
            self.write_manifests(path)
            result = add_builtin_vectorstores(user_profile=self.user_profile, path=path)
        self.assertTrue(result.success, result.failed)
        self.assertEqual(len(result.applied), 3)
        self.assertEqual(list(result.skipped), [f"example_support_articles_{self.hash_suffix}"])
        vectorstores = VectorstoreMeta.objects.filter(user_profile=self.user_profile, name__endswith=self.hash_suffix)
        self.assertEqual(vectorstores.count(), 3)
        self.assertTrue(all(v.status == "pending" and v.deployed_at is None for v in vectorstores))
        self.assertEqual(self.kubernetes.applied, [])
