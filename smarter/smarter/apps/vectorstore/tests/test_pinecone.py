"""Test the Pinecone backend, with a mock Pinecone client: :mod:`smarter.apps.vectorstore.backends.pinecone`."""

from unittest.mock import MagicMock, patch

from smarter.apps.vectorstore.backends import (
    PineconeBackend,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
    get_backend,
)

from .base_classes import VectorstoreTestBase


class TestPineconeBackend(VectorstoreTestBase):
    """Test the Pinecone backend's calls of the Pinecone API."""

    def backend(self, **spec_overrides) -> tuple[PineconeBackend, MagicMock]:
        spec = {
            "backend": "pinecone",
            "hosting": "managed",
            "selfHosted": None,
            "pinecone": {"cloud": "gcp", "region": "europe-west4"},
        }
        spec.update(spec_overrides)
        vectorstore = self.new_vectorstore("test_pinecone", **spec)
        vectorstore.index_name = vectorstore.default_index_name()
        client = MagicMock()
        return PineconeBackend(vectorstore, client=client), client

    def test_get_backend(self):
        backend, _ = self.backend()
        self.assertIsInstance(get_backend(backend.vectorstore), PineconeBackend)

    def test_create(self):
        """Test that the index is serverless, in the spec's cloud and region, with its dimension, metric and protection."""
        backend, client = self.backend()
        backend.vectorstore.deletion_protection = True
        backend.create()
        kwargs = client.create_index.call_args.kwargs
        self.assertEqual(kwargs["name"], backend.index_name)
        self.assertEqual((kwargs["spec"].cloud, kwargs["spec"].region), ("gcp", "europe-west4"))
        self.assertEqual((kwargs["dimension"], kwargs["metric"]), (32, "cosine"))
        self.assertEqual(kwargs["deletion_protection"], "enabled")

    def test_lifecycle(self):
        backend, client = self.backend()
        client.has_index.return_value = True
        client.describe_index.return_value.status = {"ready": False}
        self.assertEqual(backend.infrastructure_ready(), (False, "Pinecone is initializing the index."))
        client.describe_index.return_value.status = {"ready": True}
        self.assertTrue(backend.infrastructure_ready()[0])
        client.Index.return_value.describe_index_stats.return_value = {"total_vector_count": 7, "dimension": 32}
        self.assertEqual(backend.stats()["vector_count"], 7)
        backend.delete(["a", "b"])
        client.Index.return_value.delete.assert_called_once_with(ids=["a", "b"])
        backend.drop()
        client.delete_index.assert_called_once_with(backend.index_name)
        client.has_index.side_effect = RuntimeError("401")
        with self.assertRaises(VectorStoreBackendConnectionError):
            backend.exists()

    def test_backups(self):
        """Test that snapshots are Pinecone backups, and that restoring replaces the index."""
        backend, client = self.backend()
        client.create_backup.return_value.to_dict.return_value = {
            "backup_id": "bk-1",
            "status": "Ready",
            "size_bytes": 99,
        }
        info = backend.create_snapshot("nightly")
        self.assertEqual((info.name, info.size_bytes, info.ready), ("bk-1", 99, True))
        backend.delete_snapshot("bk-1")
        client.delete_backup.assert_called_once_with(backup_id="bk-1")
        client.has_index.return_value = True
        backend.restore_snapshot("bk-1")
        client.delete_index.assert_called_once()
        self.assertEqual(client.create_index_from_backup.call_args.kwargs["backup_id"], "bk-1")
        client.create_backup.side_effect = RuntimeError("Backups require a paid plan")
        with self.assertRaisesRegex(VectorStoreBackendError, "paid plan"):
            backend.create_snapshot("nightly")

    def test_search(self):
        """Test that searches go through PineconeVectorStore, with the metadata filter, and the score threshold."""
        backend, _ = self.backend()
        backend._embeddings = MagicMock()  # pylint: disable=protected-access
        document = MagicMock(id="c1", page_content="text", metadata={"team": "a"})
        with patch("smarter.apps.vectorstore.backends.pinecone.PineconeVectorStore") as store:
            store.return_value.similarity_search_with_score.return_value = [(document, 0.9), (document, 0.2)]
            results = backend.search("q", k=2, metadata_filter={"team": "a"})
            self.assertEqual([r.score for r in results], [0.9, 0.2])
            store.return_value.similarity_search_with_score.assert_called_with("q", k=2, filter={"team": "a"})
            results = backend.search("q", search_type="similarity_score_threshold", score_threshold=0.5)
            self.assertEqual([r.score for r in results], [0.9])

    def test_requires_api_key(self):
        """Test that a Pinecone vectorstore without an ApiConnection API key cannot connect."""
        vectorstore = self.new_vectorstore(
            "test_pinecone_no_key", backend="pinecone", hosting="managed", selfHosted=None
        )
        vectorstore.connection = None
        with self.assertRaises(VectorStoreBackendConnectionError):
            _ = PineconeBackend(vectorstore).client
