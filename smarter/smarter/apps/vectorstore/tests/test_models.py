"""Test the vectorstore models."""

from smarter.apps.vectorstore.models import (
    PAGE_BREAK,
    VectorstoreDocument,
    VectorstoreDocumentSource,
)

from .base_classes import VectorstoreTestBase


class TestVectorstoreModels(VectorstoreTestBase):
    """Test VectorstoreMeta and VectorstoreDocument."""

    def test_names(self):
        """Test the index name, unique on a shared service, and the Kubernetes name, stable across renames."""
        self_hosted = self.new_vectorstore("test_models_names")
        self.assertEqual(self_hosted.default_index_name(), self_hosted.name.replace("_", "-"))
        self.assertEqual(self_hosted.kubernetes_name, f"vectorstore-{self_hosted.pk}")
        self_hosted.rename(new_name=f"renamed_{self.hash_suffix}")
        self.assertEqual(self_hosted.kubernetes_name, f"vectorstore-{self_hosted.pk}")

        account = self.account.account_number.replace("-", "")
        managed = self.new_vectorstore("test_models_managed", hosting="managed", selfHosted=None)
        self.assertTrue(managed.default_index_name().endswith(account))
        pinecone = self.new_vectorstore(
            "test_models_pinecone_with_a_very_long_name_indeed", backend="pinecone", hosting="managed", selfHosted=None
        )
        index_name = pinecone.default_index_name()
        self.assertLessEqual(len(index_name), 45)
        self.assertTrue(index_name.endswith(account))
        self.assertRegex(index_name, r"^[a-z0-9-]+$")

    def test_properties(self):
        vectorstore = self.new_vectorstore("test_models_properties")
        self.assertTrue(vectorstore.is_self_hosted)
        self.assertFalse(vectorstore.is_deployed)
        self.assertEqual(vectorstore.maintenance["snapshotRetention"], 2)
        self.assertTrue(vectorstore.is_billable_resource)
        self.assertIn("qdrant", str(vectorstore))

    def test_document_chunk_ids(self):
        """Test that chunk ids are UUIDs, deterministic, and unique per document and chunk."""
        vectorstore = self.new_vectorstore("test_models_chunks")
        document = VectorstoreDocument.objects.create(
            vectorstore=vectorstore,
            name="a.txt",
            source=VectorstoreDocumentSource.TEXT,
            content=f"page one{PAGE_BREAK}page two",
            sha256="a" * 64,
            chunk_count=3,
        )
        self.assertEqual(document.pages, ["page one", "page two"])
        ids = document.chunk_ids()
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(ids, document.chunk_ids(3))
        self.assertRegex(ids[0], r"^[0-9a-f-]{36}$")
