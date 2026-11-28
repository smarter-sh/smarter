"""Test the Celery tasks of the vectorstore app.

They are called directly, i.e. synchronously.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone

from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore import tasks
from smarter.apps.vectorstore.deployment import DEPLOY_CHECK_INTERVAL
from smarter.apps.vectorstore.models import (
    VectorstoreDocument,
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreStatus,
)

from .base_classes import VectorstoreTestBase


class TestVectorstoreTasks(VectorstoreTestBase):
    """Test the tasks, with the test's service in place of the default one."""

    def patch_service(self, service):
        """
        Make the tasks use the test's service, with its in-memory Qdrant and fake embeddings, for its vectorstore.

        Any other vectorstore in the database, e.g. a developer's, gets a service that does nothing, so that
        the scheduled tasks, which run for every vectorstore, neither count it nor reach its database.
        """

        def service_for(vectorstore):
            if vectorstore.pk == service.vectorstore.pk:
                return service
            idle = MagicMock()
            idle.maintain.return_value = {"retry": []}
            idle.reconcile.return_value = vectorstore.status
            return idle

        patcher = patch.object(tasks, "VectorstoreService", side_effect=service_for)
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

    def test_deploy(self):
        """Test that the deploy task checks once, and queues itself again until the vectorstore is ready."""
        service = self.service(self.new_vectorstore("test_tasks_deploy"))
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        state = service.deploy()
        self.patch_service(service)
        pk = service.vectorstore.pk
        with patch.object(tasks.deploy_vectorstore, "apply_async") as again:
            self.assertEqual(tasks.deploy_vectorstore(pk, state.id), VectorstoreStatus.PROVISIONING)
            again.assert_called_once_with(
                kwargs={"vectorstore_id": pk, "deployment_id": state.id}, countdown=DEPLOY_CHECK_INTERVAL
            )
            again.reset_mock()
            self.kubernetes.statefulset = {"status": {"readyReplicas": 1}}
            self.assertEqual(tasks.deploy_vectorstore(pk, state.id), VectorstoreStatus.READY)
            again.assert_not_called()
            self.assertIsNone(tasks.deploy_vectorstore(0, state.id))

    def test_reconcile(self):
        """Test that reconcile takes over a deploy that lost its task, and brings it to ready."""
        service = self.service(self.new_vectorstore("test_tasks_reconcile"))
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        self.deploy_now(service)
        self.assertEqual(service.vectorstore.status, VectorstoreStatus.PROVISIONING)
        service.deployment.nextRetryAt = timezone.now() - timedelta(hours=1)
        service.save_deployment()
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

    def test_provision_vectorstore(self):
        """The task applies a self-hosted server's changed spec; a cluster error is the vectorstore's message."""
        service = self.ready_service("test_tasks_provision")
        self.patch_service(service)
        applied_before = len(self.kubernetes.applied)
        self.assertEqual(tasks.provision_vectorstore(service.vectorstore.pk), VectorstoreStatus.READY)
        self.assertGreater(len(self.kubernetes.applied), applied_before)
        self.kubernetes.fail_apply = "the cluster refused"
        self.assertEqual(tasks.provision_vectorstore(service.vectorstore.pk), VectorstoreStatus.READY)
        service.vectorstore.refresh_from_db()
        self.assertTrue(service.vectorstore.status_message.startswith("Provisioning failed: "))
        self.assertIn("the cluster refused", service.vectorstore.status_message)
        self.assertIsNone(tasks.provision_vectorstore(0))

    def test_undeploy_vectorstore(self):
        """The task stops serving; a failure keeps the status, with why."""
        service = self.ready_service("test_tasks_undeploy")
        self.patch_service(service)
        with patch.object(service.backend, "stop", side_effect=RuntimeError("the cluster is away")):
            self.assertEqual(tasks.undeploy_vectorstore(service.vectorstore.pk), VectorstoreStatus.READY)
        service.vectorstore.refresh_from_db()
        self.assertEqual(service.vectorstore.status_message, "Undeploy failed: the cluster is away")
        self.assertEqual(tasks.undeploy_vectorstore(service.vectorstore.pk), VectorstoreStatus.STOPPED)
        self.assertIsNone(tasks.undeploy_vectorstore(0))

    def test_delete_vectorstore(self):
        """The task destroys the database, then deletes the vectorstore and its api key Secret."""
        service = self.ready_service("test_tasks_delete")
        self.patch_service(service)
        vectorstore = service.vectorstore
        secret = vectorstore.api_key_secret
        assert secret is not None
        secret_id = secret.pk
        self.assertTrue(tasks.delete_vectorstore(vectorstore.pk))
        self.assertFalse(VectorstoreMeta.objects.filter(pk=vectorstore.pk).exists())
        self.assertFalse(Secret.objects.filter(pk=secret_id).exists())
        self.assertIn("persistentvolumeclaim", self.kubernetes.deleted[-1][0])
        self.assertFalse(tasks.delete_vectorstore(0))

    def test_a_failed_delete_keeps_the_vectorstore(self):
        """DeletionProtection enabled since the deletion was queued, or a backend error, keeps it, with why."""
        service = self.ready_service("test_tasks_delete_failed")
        self.patch_service(service)
        vectorstore = service.vectorstore
        VectorstoreMeta.objects.filter(pk=vectorstore.pk).update(deletion_protection=True)
        vectorstore.refresh_from_db()
        self.assertFalse(tasks.delete_vectorstore(vectorstore.pk))
        vectorstore.refresh_from_db()
        self.assertTrue(vectorstore.status_message.startswith("Delete failed: "))
        VectorstoreMeta.objects.filter(pk=vectorstore.pk).update(deletion_protection=False)
        vectorstore.refresh_from_db()
        with patch.object(service.backend, "destroy", side_effect=RuntimeError("the database is away")):
            self.assertFalse(tasks.delete_vectorstore(vectorstore.pk))
        vectorstore.refresh_from_db()
        self.assertEqual(vectorstore.status, VectorstoreStatus.FAILED)
        self.assertIn("the database is away", vectorstore.status_message)
