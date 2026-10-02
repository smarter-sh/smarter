"""Test the vectorstore service layer: :mod:`smarter.apps.vectorstore.service`."""

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from smarter.apps.vectorstore.models import (
    PAGE_BREAK,
    VectorstoreDocument,
    VectorstoreDocumentStatus,
    VectorstoreSnapshot,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.service import VectorstoreService, VectorstoreServiceError
from smarter.apps.vectorstore.signals import vectorstore_status_changed
from smarter.common.exceptions import SmarterValueError

from .base_classes import VectorstoreTestBase

TEXT = PAGE_BREAK.join(
    [
        "Smarter is a platform for building AI applications with manifests. " * 6,
        "Qdrant is a vector database. It stores the embeddings of documents. " * 6,
    ]
)


class TestVectorstoreService(VectorstoreTestBase):
    """Test the lifecycle, documents, search and maintenance of a vectorstore."""

    def test_deploy_self_hosted(self):
        """Test that deploy applies the server, generates its API key, and creates the collection once it is ready."""
        service = self.service(self.new_vectorstore("test_service_deploy"))
        received = []
        handler = lambda sender, **kwargs: received.append(kwargs["status"])  # noqa: E731
        vectorstore_status_changed.connect(handler)
        self.addCleanup(vectorstore_status_changed.disconnect, handler)
        service.deploy()
        vectorstore = service.vectorstore
        self.assertEqual(vectorstore.status, VectorstoreStatus.READY)
        self.assertEqual(len(self.kubernetes.applied), 1)
        self.assertIsNotNone(vectorstore.api_key_secret)
        self.assertTrue(vectorstore.api_key_secret.name.startswith("vectorstore_"))  # type: ignore[union-attr]
        self.assertIn(vectorstore.kubernetes_name, vectorstore.endpoint_url)
        self.assertEqual(vectorstore.index_name, vectorstore.default_index_name())
        self.assertIsNotNone(vectorstore.deployed_at)
        self.assertTrue(service.backend.exists())
        self.assertEqual(received, [VectorstoreStatus.PROVISIONING, VectorstoreStatus.READY])

    def test_provisioning_until_ready(self):
        """Test that a server that is starting stays provisioning, and reconcile makes it ready once it has started."""
        service = self.service(self.new_vectorstore("test_service_provisioning"))
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        service.deploy()
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.PROVISIONING)
        self.assertFalse(service.backend.exists())
        self.kubernetes.statefulset = {"status": {"readyReplicas": 1}}
        self.assertEqual(service.reconcile(), VectorstoreStatus.READY)
        self.assertTrue(service.backend.exists())

    def test_deploy_failure_and_inactive(self):
        service = self.service(self.new_vectorstore("test_service_failure"))
        self.kubernetes.fail_apply = "quota exceeded"
        with self.assertRaises(Exception):
            service.deploy()
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.FAILED)
        self.assertIn("quota exceeded", service.vectorstore.status_message)
        inactive = self.service(self.new_vectorstore("test_service_inactive"))
        inactive.vectorstore.is_active = False
        with self.assertRaises(VectorstoreServiceError):
            inactive.deploy()

    def test_documents(self):
        """Test adding, loading, reloading with fewer chunks, and deleting a document."""
        service = self.ready_service("test_service_documents")
        document, created = service.add_document(name="guide.txt", text=TEXT, metadata={"source_system": "wiki"})
        self.assertTrue(created)
        duplicate, created = service.add_document(name="copy.txt", text=TEXT)
        self.assertFalse(created)
        self.assertEqual(duplicate.pk, document.pk)

        chunks = service.load_document(document)
        document.refresh_from_db()
        self.assertEqual(document.status, VectorstoreDocumentStatus.LOADED)
        self.assertEqual(document.chunk_count, chunks)
        self.assertEqual(service.refresh_stats()["vector_count"], chunks)

        # every chunk records its document, page and the document's metadata.
        result = service.search("vector database", k=1)[0]
        self.assertEqual(result.metadata["document_id"], document.pk)
        self.assertEqual(result.metadata["source_system"], "wiki")
        self.assertIn(result.metadata["page"], (1, 2))

        # loaded again with larger chunks, the chunks that it no longer has are removed.
        service.vectorstore.spec["embeddings"]["chunkSize"] = 4000
        self.assertLess(service.load_document(document), chunks)
        document.refresh_from_db()
        self.assertEqual(service.refresh_stats()["vector_count"], document.chunk_count)

        service.delete_document(document)
        self.assertFalse(VectorstoreDocument.objects.filter(pk=document.pk).exists())
        self.assertEqual(service.refresh_stats()["vector_count"], 0)

    def test_load_failure(self):
        service = self.ready_service("test_service_load_failure")
        document, _ = service.add_document(name="a.txt", text=TEXT)
        with patch.object(service.backend, "upsert", side_effect=RuntimeError("embeddings API is down")):
            with self.assertRaises(RuntimeError):
                service.load_document(document)
        document.refresh_from_db()
        self.assertEqual(document.status, VectorstoreDocumentStatus.FAILED)
        self.assertIn("embeddings API is down", document.status_message)

    def test_search(self):
        """Test the search types, the metadata filter, and the validation of search arguments."""
        service = self.ready_service("test_service_search")
        first, _ = service.add_document(name="a.txt", text=TEXT, metadata={"team": "a"})
        second, _ = service.add_document(
            name="b.txt", text="Pinecone is a managed vector database. " * 10, metadata={"team": "b"}
        )
        service.load_document(first)
        service.load_document(second)
        self.assertEqual(len(service.search("vectors", k=3)), 3)
        self.assertEqual(len(service.search("vectors", k=2, search_type="mmr", fetch_k=10)), 2)
        filtered = service.search("vectors", k=10, metadata_filter={"team": "b"})
        self.assertTrue(filtered)
        self.assertTrue(all(r.metadata["team"] == "b" for r in filtered))
        self.assertEqual(service.search("vectors", search_type="similarity_score_threshold", score_threshold=1.01), [])
        for kwargs in (
            {"query": " "},
            {"query": "x", "search_type": "fuzzy"},
            {"query": "x", "search_type": "similarity_score_threshold"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(SmarterValueError):
                service.search(**kwargs)

    def test_not_ready(self):
        service = self.service(self.new_vectorstore("test_service_not_ready"))
        with self.assertRaises(VectorstoreServiceError):
            service.search("anything")
        document, _ = service.add_document(name="a.txt", text=TEXT)
        with self.assertRaises(VectorstoreServiceError):
            service.load_document(document)

    def test_undeploy_and_destroy(self):
        """Test that undeploy keeps the volume, destroy removes it, and deletionProtection prevents it."""
        service = self.ready_service("test_service_destroy")
        document, _ = service.add_document(name="a.txt", text=TEXT)
        service.load_document(document)
        service.undeploy()
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.STOPPED)
        self.assertNotIn("persistentvolumeclaim", self.kubernetes.deleted[-1][0])

        service.destroy()
        self.assertIn("persistentvolumeclaim", self.kubernetes.deleted[-1][0])
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.PENDING)
        document.refresh_from_db()
        self.assertEqual((document.status, document.chunk_count), (VectorstoreDocumentStatus.PENDING, 0))

        protected = self.ready_service(
            "test_service_protected", index={"dimension": 32, "metric": "cosine", "deletionProtection": True}
        )
        protected.vectorstore.deletion_protection = True
        with self.assertRaisesRegex(VectorstoreServiceError, "deletionProtection"):
            protected.destroy()
        self.assertEqual(protected.vectorstore.status, VectorstoreStatus.READY)

    def test_managed_qdrant_connection(self):
        """Test that a managed Qdrant database is reached at its ApiConnection's URL, with its API key."""
        vectorstore = self.new_vectorstore("test_service_managed", hosting="managed", selfHosted=None)
        service = VectorstoreService(vectorstore)
        with patch("smarter.apps.vectorstore.backends.qdrant.QdrantClient") as client:
            _ = service.backend.client
        client.assert_called_once_with(url="https://qdrant.example.com:6333", api_key="test-api-key", timeout=30)
        self.assertEqual(service.backend.infrastructure_ready(), (True, ""))

    def test_snapshots(self):
        """Test snapshots, their retention, and restoring one."""
        service = self.ready_service("test_service_snapshots")
        backend = self.mock_snapshots(service)
        for _ in range(3):
            service.snapshot()
        self.assertEqual(service.vectorstore.snapshots.count(), 3)  # type: ignore[attr-defined]
        self.assertIsNotNone(service.vectorstore.last_snapshot_at)
        self.assertEqual(service.prune_snapshots(), 1)  # snapshotRetention is 2
        self.assertEqual(backend.delete_snapshot.call_count, 1)
        newest = service.vectorstore.snapshots.order_by("-created_at").first()  # type: ignore[attr-defined]
        service.restore(newest)
        backend.restore_snapshot.assert_called_once_with(newest.name)

        backend.create_snapshot.side_effect = RuntimeError("disk full")
        with self.assertRaises(RuntimeError):
            service.snapshot()
        self.assertTrue(VectorstoreSnapshot.objects.filter(vectorstore=service.vectorstore, status="failed").exists())
        service.prune_snapshots()
        self.assertFalse(VectorstoreSnapshot.objects.filter(vectorstore=service.vectorstore, status="failed").exists())

    def test_maintain(self):
        """Test that maintenance takes a snapshot when one is due, prunes, and finds documents whose task was lost."""
        service = self.ready_service("test_service_maintain")
        self.mock_snapshots(service)
        stuck, _ = service.add_document(name="stuck.txt", text=TEXT)
        VectorstoreDocument.objects.filter(pk=stuck.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        result = service.maintain()
        self.assertEqual(result["status"], VectorstoreStatus.READY)
        self.assertIsNotNone(result["snapshot"])
        self.assertEqual(result["retry"], [stuck.pk])
        self.assertIsNotNone(service.vectorstore.last_maintenance_at)
        # the next snapshot is not due for 24 hours.
        self.assertFalse(service.snapshot_due())
        self.assertIsNone(service.maintain()["snapshot"])
        self.assertTrue(service.snapshot_due(timezone.now() + timedelta(hours=25)))
        service.vectorstore.spec["maintenance"]["snapshots"] = False
        self.assertFalse(service.snapshot_due(timezone.now() + timedelta(hours=25)))
