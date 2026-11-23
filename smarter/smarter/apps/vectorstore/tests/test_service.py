"""Test the vectorstore service layer: :mod:`smarter.apps.vectorstore.service`."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone
from httpx import Headers
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from smarter.apps.vectorstore.backends import (
    QdrantBackend,
    VectorStoreBackendCredentialsError,
    VectorStoreBackendRejectedError,
)
from smarter.apps.vectorstore.deployment import (
    CREDENTIALS,
    DEPLOY_CHECK_INTERVAL,
    FALSE,
    INDEX,
    SERVER,
    TRUE,
    UNKNOWN,
    VOLUME,
    VectorstoreDeploymentState,
)
from smarter.apps.vectorstore.models import (
    PAGE_BREAK,
    VectorstoreDocument,
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreSnapshot,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.service import VectorstoreService, VectorstoreServiceError
from smarter.apps.vectorstore.signals import vectorstore_status_changed
from smarter.apps.vectorstore.sources import DocumentSource
from smarter.common.exceptions import SmarterValueError
from smarter.lib.typing import SmarterDictType

from .base_classes import VectorstoreTestBase

TEXT = PAGE_BREAK.join(
    [
        "Smarter is a platform for building AI applications with manifests. " * 6,
        "Qdrant is a vector database. It stores the embeddings of documents. " * 6,
    ]
)


class TestVectorstoreService(VectorstoreTestBase):
    """Test the lifecycle, documents, search and maintenance of a vectorstore."""

    def test_repr(self):
        """Test that the service and its backend name their vectorstore in their repr."""
        service = self.service(self.new_vectorstore("test_service_repr"))
        name = service.vectorstore.name
        self.assertEqual(repr(service), f"<VectorstoreService vectorstore={name}>")
        self.assertEqual(repr(service.backend), f"<{service.backend.__class__.__name__} vectorstore={name}>")

    def test_deploy_self_hosted(self):
        """Test that deploy queues the deploy task, whose check applies the server and creates the collection."""
        service = self.service(self.new_vectorstore("test_service_deploy"))
        received = []
        handler = lambda sender, **kwargs: received.append(kwargs["status"])  # noqa: E731
        vectorstore_status_changed.connect(handler)
        self.addCleanup(vectorstore_status_changed.disconnect, handler)
        state = service.deploy()
        vectorstore = service.vectorstore
        self.assertEqual(vectorstore.status, VectorstoreStatus.PROVISIONING)
        self.deploy_task.assert_called_once_with(vectorstore.pk, state.id)
        self.assertEqual(self.kubernetes.applied, [], "deploy itself creates nothing")
        self.assertIsNotNone(vectorstore.api_key_secret)
        self.assertTrue(vectorstore.api_key_secret.name.startswith("vectorstore_"))  # type: ignore[union-attr]
        self.assertEqual(self.conditions(service), {CREDENTIALS: (TRUE, "Accepted"), INDEX: (UNKNOWN, "Pending")})

        self.assertIsNone(service.deployment_step(state.id))
        self.assertEqual(vectorstore.status, VectorstoreStatus.READY)
        self.assertEqual(len(self.kubernetes.applied), 1)
        self.assertIn(vectorstore.kubernetes_name, vectorstore.endpoint_url)
        self.assertEqual(vectorstore.index_name, vectorstore.default_index_name())
        self.assertIsNotNone(vectorstore.deployed_at)
        self.assertTrue(service.backend.exists())
        self.assertEqual(received, [VectorstoreStatus.PROVISIONING, VectorstoreStatus.READY])
        self.assertEqual(
            self.conditions(service),
            {
                CREDENTIALS: (TRUE, "Accepted"),
                VOLUME: (TRUE, "Bound"),
                SERVER: (TRUE, "Ready"),
                INDEX: (TRUE, "Ready"),
            },
        )
        stored = VectorstoreDeploymentState.of(VectorstoreMeta.objects.get(pk=vectorstore.pk))
        self.assertEqual([c.type for c in stored.conditions], [CREDENTIALS, VOLUME, SERVER, INDEX])
        self.assertEqual((stored.attempt, stored.provisioned, stored.in_progress), (1, True, False))

    @staticmethod
    def conditions(service: VectorstoreService) -> dict[str, tuple[str, str]]:
        """The deploy's conditions, as {type: (status, reason)}."""
        return {c.type: (c.status, c.reason) for c in service.deployment.conditions}

    def test_waits_for_the_volume_then_the_server(self):
        """Test that each check records what the server waits for, and checks again every few seconds."""
        service = self.service(self.new_vectorstore("test_service_waits"))
        self.kubernetes.volume_claim = {"status": {"phase": "Pending"}}
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        state = service.deploy()
        self.assertEqual(service.deployment_step(state.id), DEPLOY_CHECK_INTERVAL)
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.PROVISIONING)
        self.assertEqual(service.vectorstore.status_message, "Waiting for a volume to be provisioned.")
        self.assertEqual(self.conditions(service)[VOLUME], (FALSE, "Pending"))
        self.assertIsNotNone(service.deployment.nextRetryAt)
        self.assertFalse(service.backend.exists())

        self.kubernetes.volume_claim = {"status": {"phase": "Bound"}}
        self.kubernetes.pods = [
            {"status": {"containerStatuses": [{"state": {"waiting": {"reason": "ImagePullBackOff", "message": "x"}}}]}}
        ]
        self.assertEqual(service.deployment_step(state.id), DEPLOY_CHECK_INTERVAL)
        self.assertEqual(self.conditions(service)[VOLUME], (TRUE, "Bound"))
        self.assertEqual(self.conditions(service)[SERVER], (FALSE, "ImagePullBackOff"))
        self.assertEqual(len(self.kubernetes.applied), 1, "the server is applied once")

        self.kubernetes.pods = []
        self.kubernetes.statefulset = {"status": {"readyReplicas": 1}}
        self.assertIsNone(service.deployment_step(state.id))
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.READY)
        self.assertEqual(service.deployment.attempt, 3)

    def test_errors_are_retried_with_backoff(self):
        """Test that an error is recorded, and checked again later after each error in a row, until it passes."""
        service = self.service(self.new_vectorstore("test_service_backoff"))
        state = service.deploy()
        self.kubernetes.fail_apply = "the api server timed out"
        self.assertEqual(service.deployment_step(state.id), DEPLOY_CHECK_INTERVAL * 2)
        self.assertEqual(service.deployment_step(state.id), DEPLOY_CHECK_INTERVAL * 4)
        vectorstore = service.vectorstore
        self.assertEqual(vectorstore.status, VectorstoreStatus.PROVISIONING)
        self.assertTrue(vectorstore.status_message.startswith("Retrying in 60s, after check 2 of 80"))
        self.assertIn("the api server timed out", str(service.deployment.lastError))
        self.kubernetes.fail_apply = None
        self.assertIsNone(service.deployment_step(state.id))
        self.assertEqual(vectorstore.status, VectorstoreStatus.READY)
        self.assertEqual(service.deployment.consecutiveErrors, 0)

    def test_a_deploy_gives_up(self):
        """Test that a deploy fails after its last check, with what it was waiting for."""
        service = self.service(self.new_vectorstore("test_service_gives_up"))
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        state = service.deploy()
        service.deployment.maxAttempts = 2
        self.assertEqual(service.deployment_step(state.id), DEPLOY_CHECK_INTERVAL)
        self.assertIsNone(service.deployment_step(state.id))
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.FAILED)
        self.assertEqual(
            service.vectorstore.status_message, "Deploy failed after 2 checks: The Qdrant server is starting."
        )
        self.assertFalse(service.deployment.in_progress)

    def test_a_refused_api_key_fails_at_once(self):
        """Test that an api key that the database refuses fails the deploy now, without queuing the task."""
        vectorstore = self.new_vectorstore("test_service_refused", hosting="managed", selfHosted=None)
        client = MagicMock()
        client.collection_exists.side_effect = UnexpectedResponse(401, "Unauthorized", b"", Headers())
        service = self.service(vectorstore, client=client)
        with self.assertRaisesRegex(VectorStoreBackendCredentialsError, "Qdrant refused the api key"):
            service.deploy()
        self.deploy_task.assert_not_called()
        self.assertEqual(vectorstore.status, VectorstoreStatus.FAILED)
        self.assertIsNone(vectorstore.deployed_at, "Celery Beat leaves it alone")
        self.assertEqual(self.conditions(service)[CREDENTIALS], (FALSE, "Refused"))

    def test_an_unreachable_database_is_checked_again(self):
        """Test that a database that can't be reached yet is no error for deploy, and the task checks it again."""
        vectorstore = self.new_vectorstore("test_service_unreachable", hosting="managed", selfHosted=None)
        client = MagicMock(wraps=QdrantClient(location=":memory:"))
        client.collection_exists.side_effect = TimeoutError("timed out")
        service = self.service(vectorstore, client=client)
        state = service.deploy()
        self.assertEqual(self.conditions(service)[CREDENTIALS], (UNKNOWN, "Unreachable"))
        self.assertEqual(service.deployment_step(state.id), DEPLOY_CHECK_INTERVAL * 2)
        client.collection_exists.side_effect = None
        client.collection_exists.return_value = False
        self.assertIsNone(service.deployment_step(state.id))
        self.assertEqual(vectorstore.status, VectorstoreStatus.READY)
        self.assertEqual(self.conditions(service)[CREDENTIALS], (TRUE, "Accepted"))

    def test_a_rejected_request_fails_at_once(self):
        """Test that a request that the database would refuse again, e.g. a full quota, fails the deploy."""
        service = self.service(self.new_vectorstore("test_service_rejected"))
        state = service.deploy()
        with patch.object(service.backend, "create", side_effect=VectorStoreBackendRejectedError("quota exceeded")):
            self.assertIsNone(service.deployment_step(state.id))
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.FAILED)
        self.assertTrue(service.vectorstore.status_message.startswith("Deploy failed: "))
        self.assertIn("quota exceeded", service.vectorstore.status_message)
        self.assertIn("quota exceeded", str(service.deployment.lastError))

    def test_a_replaced_or_undeployed_deploy_stops(self):
        """Test that the task of a deploy that another deploy replaced, or that was undeployed, does nothing."""
        service = self.service(self.new_vectorstore("test_service_replaced"))
        first = service.deploy()
        second = service.deploy()
        self.assertIsNone(service.deployment_step(first.id))
        self.assertEqual(service.deployment.attempt, 0)
        service.undeploy()
        self.assertIsNone(service.deployment_step(second.id))
        self.assertFalse(service.deployment.in_progress)
        self.assertEqual(self.kubernetes.applied, [])

    def test_reconcile_leaves_a_deploy_to_its_task_until_it_stalls(self):
        """Test that Celery Beat's reconcile doesn't check a deploy in progress, but takes over one that lost its task."""
        service = self.service(self.new_vectorstore("test_service_reconcile"))
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        state = service.deploy()
        service.deployment_step(state.id)
        self.kubernetes.statefulset = {"status": {"readyReplicas": 1}}
        self.assertEqual(service.reconcile(), VectorstoreStatus.PROVISIONING)
        service.deployment.nextRetryAt = timezone.now() - timedelta(hours=1)
        self.assertEqual(service.reconcile(), VectorstoreStatus.READY)
        self.assertFalse(service.deployment.in_progress)
        self.assertIsNotNone(service.vectorstore.last_checked_at)

    def test_reconcile_failure_and_inactive(self):
        """Test that reconcile marks a ready database failed when it can't be reached, and deploy refuses an inactive one."""
        service = self.ready_service("test_service_failure")
        with patch.object(service.backend, "exists", side_effect=RuntimeError("connection reset")):
            self.assertEqual(service.reconcile(), VectorstoreStatus.FAILED)
        self.assertEqual(service.vectorstore.status_message, "connection reset")
        self.assertEqual(service.reconcile(), VectorstoreStatus.READY)
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

    def test_add_documents(self):
        """Test that new documents are queued to load in a ready vectorstore, and that duplicates are not added again."""
        service = self.ready_service("test_service_add_documents")
        sources = [
            DocumentSource("guide.txt", None, TEXT, "text/plain", "text"),
            DocumentSource("copy.txt", None, TEXT, "text/plain", "text"),
            DocumentSource("other.txt", None, "Another document. " * 20, "text/plain", "text"),
        ]
        result = service.add_documents(sources, metadata={"team": "a"})
        self.assertEqual([d.name for d in result.added], ["guide.txt", "other.txt"])
        self.assertEqual([d.name for d in result.duplicates], ["guide.txt"])
        self.assertTrue(result.queued)
        self.assertEqual([c.args[0] for c in self.load_task.call_args_list], [d.pk for d in result.added])
        self.assertEqual(result.added[0].metadata, {"team": "a"})

    def test_documents_wait_for_the_deploy(self):
        """Test that documents added before a deploy wait, and are queued as soon as the deploy is ready."""
        service = self.service(self.new_vectorstore("test_service_documents_wait"))
        result = service.add_documents([DocumentSource("guide.txt", None, TEXT, "text/plain", "text")])
        self.assertFalse(result.queued)
        self.load_task.assert_not_called()
        self.deploy_now(service)
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.READY)
        self.load_task.assert_called_once_with(result.added[0].pk)

    def test_find_and_remove_documents(self):
        """Test that a document is found by its id or its name, and that removing it queues the task that does."""
        service = self.ready_service("test_service_find_documents")
        first, _ = service.add_document(name="guide.txt", text=TEXT)
        second, _ = service.add_document(name="guide.txt", text="A second guide. " * 20)
        third, _ = service.add_document(name="faq.txt", text="Questions. " * 20)
        self.assertEqual(service.find_document(str(third.pk)), third)
        self.assertEqual(service.find_document("faq.txt"), third)
        with self.assertRaisesRegex(VectorstoreServiceError, "several documents named guide.txt"):
            service.find_document("guide.txt")
        with self.assertRaisesRegex(VectorstoreServiceError, "has no document missing.txt"):
            service.find_document("missing.txt")
        self.assertEqual(service.find_document(str(first.pk)), first)
        removed = service.remove_document(second)
        self.assertEqual(removed.status, VectorstoreDocumentStatus.DELETING)
        self.delete_task.assert_called_once_with(second.pk)

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
        invalid: tuple[SmarterDictType, ...] = (
            {"query": " "},
            {"query": "x", "search_type": "fuzzy"},
            {"query": "x", "search_type": "similarity_score_threshold"},
        )
        for kwargs in invalid:
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
            backend = service.backend
            assert isinstance(backend, QdrantBackend)
            _ = backend.client
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
        assert newest is not None
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
