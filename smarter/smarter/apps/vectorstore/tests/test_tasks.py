"""Test the Celery tasks of the vectorstore app.

They are called directly, i.e. synchronously.
"""

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from smarter.apps.vectorstore import tasks
from smarter.apps.vectorstore.models import (
    VectorstoreDocument,
    VectorstoreDocumentStatus,
    VectorstoreStatus,
)

from .base_classes import VectorstoreTestBase


class TestVectorstoreTasks(VectorstoreTestBase):
    """Test the tasks, with the test's service in place of the default one."""

    def patch_service(self, service):
        """Make the tasks use the test's service: its in-memory Qdrant and fake embeddings."""
        patcher = patch.object(tasks, "VectorstoreService", side_effect=lambda vectorstore: service)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_load_and_delete(self):
        service = self.ready_service("test_tasks_load")
        self.patch_service(service)
        document, _ = service.add_document(name="a.txt", text="Retrieval-augmented generation. " * 30)
        chunks = tasks.load_vectorstore_document(document.pk)
        self.assertGreater(chunks, 0)
        self.assertTrue(tasks.delete_vectorstore_document(document.pk))
        self.assertFalse(VectorstoreDocument.objects.filter(pk=document.pk).exists())
        self.assertIsNone(tasks.load_vectorstore_document(0))
        self.assertFalse(tasks.delete_vectorstore_document(0))

    def test_load_failure_returns_none(self):
        service = self.service(self.new_vectorstore("test_tasks_not_ready"))
        self.patch_service(service)
        document, _ = service.add_document(name="a.txt", text="text " * 50)
        self.assertIsNone(tasks.load_vectorstore_document(document.pk))

    def test_reconcile(self):
        """Test that reconcile brings a provisioning vectorstore to ready, once its server has started."""
        service = self.service(self.new_vectorstore("test_tasks_reconcile"))
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        service.deploy()
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.PROVISIONING)
        self.patch_service(service)
        self.kubernetes.statefulset = {"status": {"readyReplicas": 1}}
        result = tasks.reconcile_vectorstores()
        self.assertEqual(result[str(service.vectorstore)], VectorstoreStatus.READY)

    def test_maintain_requeues_lost_documents(self):
        """Test that maintenance queues documents whose task was lost again, and takes a scheduled snapshot."""
        service = self.ready_service("test_tasks_maintain")
        self.mock_snapshots(service)
        self.patch_service(service)
        pending, _ = service.add_document(name="pending.txt", text="lost " * 50)
        deleting, _ = service.add_document(name="deleting.txt", text="gone " * 50)
        VectorstoreDocument.objects.filter(pk=deleting.pk).update(status=VectorstoreDocumentStatus.DELETING)
        VectorstoreDocument.objects.filter(pk__in=[pending.pk, deleting.pk]).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        with (
            patch.object(tasks.load_vectorstore_document, "delay") as load,
            patch.object(tasks.delete_vectorstore_document, "delay") as delete,
        ):
            results = tasks.maintain_vectorstores()
        load.assert_called_once_with(pending.pk)
        delete.assert_called_once_with(deleting.pk)
        self.assertIsNotNone(results[str(service.vectorstore)]["snapshot"])

    def test_snapshot_task(self):
        service = self.ready_service("test_tasks_snapshot")
        self.mock_snapshots(service)
        self.patch_service(service)
        self.assertTrue(tasks.snapshot_vectorstore(service.vectorstore.pk))
        self.assertFalse(service.vectorstore.snapshots.get().scheduled)  # type: ignore[attr-defined]
        self.assertIsNone(tasks.snapshot_vectorstore(0))
