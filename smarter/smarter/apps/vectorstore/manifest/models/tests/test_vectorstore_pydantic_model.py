"""Test the Vectorstore Pydantic manifest: :mod:`smarter.apps.vectorstore.manifest.models.vectorstore`."""

import copy
import os

from pydantic import ValidationError

from smarter.apps.vectorstore.manifest.models.vectorstore.const import (
    DEFAULT_QDRANT_IMAGE,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.model import SAMVectorstore
from smarter.apps.vectorstore.manifest.models.vectorstore.spec import SAMVectorstoreSpec
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
INVALID = (SAMValidationError, ValidationError, ValueError)


class TestVectorstoreManifest(SmarterTestBase):
    """Test SAMVectorstore and its spec's validation."""

    def setUp(self):
        super().setUp()
        self.manifest = get_readonly_yaml_file(os.path.join(HERE, "data", "vectorstore.yaml"))

    def spec(self, **overrides) -> SAMVectorstoreSpec:
        data = copy.deepcopy(self.manifest["spec"])
        data.update(overrides)
        return SAMVectorstoreSpec(**data)

    def assertInvalid(self, **overrides):
        with self.assertRaises(INVALID):
            self.spec(**overrides)

    def test_manifest(self):
        manifest = SAMVectorstore(**self.manifest)
        self.assertEqual(manifest.metadata.name, "test_vectorstore")
        spec = manifest.spec
        self.assertEqual(spec.selfHosted.image, DEFAULT_QDRANT_IMAGE)  # type: ignore[union-attr]
        self.assertEqual((spec.embeddings.chunkSize, spec.embeddings.chunkOverlap), (1000, 200))
        self.assertTrue(spec.maintenance.snapshots)
        self.assertTrue(spec.isActive)

    def test_hosting(self):
        """Test the combinations of backend, hosting, connection, selfHosted and pinecone."""
        self.spec(backend="qdrant", hosting="managed", connection="qdrant_cloud", selfHosted=None)
        self.spec(
            backend="pinecone",
            hosting="managed",
            connection="pinecone",
            selfHosted=None,
            pinecone={"region": "us-west-2"},
        )
        self.assertInvalid(backend="pinecone")  # self_hosted
        self.assertInvalid(connection="qdrant_cloud")  # self_hosted with a connection
        self.assertInvalid(hosting="managed", selfHosted=None)  # managed without a connection
        self.assertInvalid(hosting="managed", connection="qdrant_cloud")  # selfHosted while managed
        self.assertInvalid(pinecone={"region": "us-east-1"})  # pinecone while qdrant
        self.assertInvalid(backend="weaviate")
        self.assertInvalid(hosting="on_prem")

    def test_index_and_embeddings(self):
        self.assertInvalid(index={"dimension": 0})
        self.assertInvalid(index={"dimension": 20001})
        self.assertInvalid(index={"dimension": 1536, "metric": "manhattan"})
        self.assertInvalid(index={"dimension": 1536, "name": "Not_Valid"})
        self.spec(index={"dimension": 1536, "name": "my-index-2"})
        self.assertInvalid(embeddings={"provider": "openai", "model": "m", "dimensions": 768})  # != index.dimension
        self.assertInvalid(embeddings={"provider": "openai", "model": "m", "chunkSize": 500, "chunkOverlap": 500})
        self.assertInvalid(embeddings={"provider": "", "model": "m"})

    def test_self_hosted(self):
        self.spec(selfHosted={"storage": "500Gi", "cpu": "2", "memory": "8Gi", "storageClass": "gp3"})
        for field, value in (("storage", "ten gigs"), ("cpu", "-1"), ("memory", "1 GB"), ("image", "Qdrant:Latest!")):
            with self.subTest(field=field):
                self.assertInvalid(selfHosted={field: value})

    def test_maintenance(self):
        self.spec(maintenance={"snapshots": False})
        self.assertInvalid(maintenance={"snapshotIntervalHours": 0})
        self.assertInvalid(maintenance={"snapshotRetention": 101})

    def test_immutable(self):
        manifest = SAMVectorstore(**self.manifest)
        with self.assertRaises(ValidationError):
            manifest.spec.backend = "pinecone"  # type: ignore[misc]
