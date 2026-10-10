"""Test the Pinecone backend, with a mock Pinecone client: :mod:`smarter.apps.vectorstore.backends.pinecone`."""

from unittest.mock import MagicMock

from pinecone.core.openapi.db_data.models import QueryResponse, ScoredVector

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

    def test_upsert(self):
        """Test that chunks are embedded and upserted in batches, with their text in the metadata."""
        backend, client = self.backend()
        backend._embeddings = MagicMock()  # pylint: disable=protected-access
        backend.embeddings.embed_documents.side_effect = lambda texts: [[float(len(text))] for text in texts]
        backend.upsert(["c1", "c2", "c3"], ["a", "bb", "ccc"], [{"team": "a"}, {}, {"team": "c"}], batch_size=2)
        upsert = client.Index.return_value.upsert
        self.assertEqual(upsert.call_count, 2)
        self.assertEqual(
            upsert.call_args_list[0].kwargs["vectors"],
            [
                {"id": "c1", "values": [1.0], "metadata": {"team": "a", "text": "a"}},
                {"id": "c2", "values": [2.0], "metadata": {"text": "bb"}},
            ],
        )
        self.assertEqual(
            upsert.call_args_list[1].kwargs["vectors"],
            [{"id": "c3", "values": [3.0], "metadata": {"team": "c", "text": "ccc"}}],
        )

    def test_search(self):
        """Test that searches query the index with the query's embedding, the metadata filter, and the score.

        threshold, and that vectors without text are skipped.
        """
        backend, client = self.backend()
        backend._embeddings = MagicMock()  # pylint: disable=protected-access
        backend.embeddings.embed_query.return_value = [1.0, 0.0]
        query = client.Index.return_value.query
        query.return_value = QueryResponse(
            matches=[
                ScoredVector(id="c1", score=0.9, metadata={"text": "one", "team": "a"}),
                ScoredVector(id="c2", score=0.2, metadata={"text": "two", "team": "a"}),
                ScoredVector(id="x", score=0.8, metadata={"team": "a"}),
            ],
            namespace="",
            _check_type=False,
        )
        results = backend.search("q", k=3, metadata_filter={"team": "a"})
        self.assertEqual([(r.id, r.text, r.score) for r in results], [("c1", "one", 0.9), ("c2", "two", 0.2)])
        self.assertEqual(results[0].metadata, {"team": "a"})
        query.assert_called_with(vector=[1.0, 0.0], top_k=3, include_metadata=True, filter={"team": "a"})
        results = backend.search("q", search_type="similarity_score_threshold", score_threshold=0.5)
        self.assertEqual([r.score for r in results], [0.9])

    def test_search_mmr(self):
        """Test that MMR fetches fetch_k matches with their values, and prefers diverse ones."""
        backend, client = self.backend()
        backend._embeddings = MagicMock()  # pylint: disable=protected-access
        backend.embeddings.embed_query.return_value = [1.0, 0.0]
        query = client.Index.return_value.query
        query.return_value = {
            "matches": [
                {"id": "c1", "score": 0.99, "values": [1.0, 0.0], "metadata": {"text": "one"}},
                {"id": "c2", "score": 0.98, "values": [0.99, 0.01], "metadata": {"text": "near duplicate"}},
                {"id": "c3", "score": 0.7, "values": [0.7, 0.7], "metadata": {"text": "different"}},
            ]
        }
        results = backend.search("q", k=2, search_type="mmr", fetch_k=3, lambda_mult=0.3)
        self.assertEqual([r.id for r in results], ["c1", "c3"])
        self.assertEqual([r.score for r in results], [None, None])
        self.assertEqual(query.call_args.kwargs["top_k"], 3)
        self.assertTrue(query.call_args.kwargs["include_values"])
        query.return_value = {"matches": []}
        self.assertEqual(backend.search("q", search_type="mmr"), [])
        self.assertEqual(query.call_args.kwargs["top_k"], 20)

    def test_requires_api_key(self):
        """Test that a Pinecone vectorstore without an ApiConnection API key cannot connect."""
        vectorstore = self.new_vectorstore(
            "test_pinecone_no_key", backend="pinecone", hosting="managed", selfHosted=None
        )
        vectorstore.connection = None
        with self.assertRaises(VectorStoreBackendConnectionError):
            _ = PineconeBackend(vectorstore).client
