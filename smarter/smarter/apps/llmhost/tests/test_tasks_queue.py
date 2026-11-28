"""
Test how the web server queues changes to LLMHosts and computes: :mod:`smarter.apps.llmhost.tasks.queue`.

Also the callers that only queue: LLMHostCompute's ``pre_delete`` receiver, and the admin's reconcile action. The
tasks are held (:meth:`~smarter.apps.llmhost.tests.base_classes.InMemoryLLMHostInfrastructureMixin.holding_queued_tasks`),
so each test sees what the request itself did: it checks, records a message, and writes nothing to the cluster.
"""

from unittest.mock import MagicMock

from smarter.apps.llmhost.admin import LLMHostComputeAdmin
from smarter.apps.llmhost.manifest.brokers.llmhost_compute import (
    compute_spec_to_django_orm,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostQueuedMessage
from smarter.apps.llmhost.manifest.models.llmhost_compute.spec import (
    SAMLLMHostComputeSpec,
)
from smarter.apps.llmhost.models import LLMHostCompute
from smarter.apps.llmhost.models.compute import LLMHostComputeNodeGroupStatus
from smarter.apps.llmhost.services import (
    LLMHostClusterError,
    LLMHostConfigurationError,
)
from smarter.apps.llmhost.tasks import (
    queue_delete,
    queue_destroy,
    queue_launch,
    queue_reconcile,
)

from .base_classes import LLMHostTestBase


class TestQueue(LLMHostTestBase):
    """Each queue_* function checks what it can, records what it queued, and queues its task, which it doesn't run."""

    def own_compute(self, name: str) -> LLMHostCompute:
        """An LLMHostCompute of the test user, deleted when the test ends."""
        spec = SAMLLMHostComputeSpec.model_validate(
            {
                "node": {"instanceType": "g6.2xlarge", "cpu": 8, "memoryGb": 32},
                "nodeGroup": {"maxNodes": 2},
                "cost": {"perHour": "1.0"},
            }
        )
        compute = LLMHostCompute.objects.create(
            name=name, user_profile=self.user_profile, **compute_spec_to_django_orm(spec)
        )
        self.addCleanup(LLMHostCompute.objects.filter(pk=compute.pk).delete)
        return compute

    def test_queue_launch(self):
        llmhost = self.new_llmhost("test_queue_launch")
        with self.holding_queued_tasks() as queued:
            observation = queue_launch(llmhost)
        self.assertEqual(observation.message, SAMLLMHostQueuedMessage.LAUNCH.value)
        self.assertEqual(observation.status, llmhost.status)
        queued["launch_llmhost"].assert_called_once_with(llmhost.pk)
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status_message, SAMLLMHostQueuedMessage.LAUNCH.value)
        self.assertEqual(self.cluster.applied, [])
        self.assertEqual(self.nodegroups.created, [])

    def test_queue_launch_refuses_at_once(self):
        """What can be checked without writing is an error now, and nothing is queued."""
        llmhost = self.new_llmhost("test_queue_launch_refused", model={"tokenSecret": "test_llmhost_no_such_secret"})
        with self.holding_queued_tasks() as queued:
            with self.assertRaises(LLMHostConfigurationError):
                queue_launch(llmhost)
            self.cluster.ready = False
            with self.assertRaises(LLMHostClusterError):
                queue_launch(self.new_llmhost("test_queue_launch_no_cluster"))
        queued["launch_llmhost"].assert_not_called()
        llmhost.refresh_from_db()
        self.assertNotEqual(llmhost.status_message, SAMLLMHostQueuedMessage.LAUNCH.value)

    def test_queue_destroy(self):
        llmhost = self.new_llmhost("test_queue_destroy")
        with self.holding_queued_tasks() as queued:
            queue_destroy(llmhost, purge=True)
            self.cluster.ready = False
            with self.assertRaises(LLMHostClusterError):
                queue_destroy(llmhost)
        queued["destroy_llmhost"].assert_called_once_with(llmhost.pk, purge=True)
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status_message, SAMLLMHostQueuedMessage.UNDEPLOY.value)
        self.assertEqual(self.cluster.deleted, [])

    def test_queue_delete(self):
        """An LLMHost is kept until its task deletes it; a deployed one needs the cluster."""
        llmhost = self.new_llmhost("test_queue_delete")
        deployed = self.new_llmhost("test_queue_delete_deployed")
        deployed.status = "pending"
        deployed.save(update_fields=["status"])
        self.cluster.ready = False
        with self.holding_queued_tasks() as queued:
            # an LLMHost that isn't deployed has nothing in the cluster to destroy.
            queue_delete(llmhost)
            with self.assertRaises(LLMHostClusterError):
                queue_delete(deployed)
        queued["delete_llmhost"].assert_called_once_with(llmhost.pk)
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status_message, SAMLLMHostQueuedMessage.DELETE.value)

    def test_queue_reconcile(self):
        compute = self.own_compute("test_queue_reconcile")
        with self.holding_queued_tasks() as queued:
            queue_reconcile(compute)
        queued["reconcile_llmhost_compute"].assert_called_once_with(compute.pk)
        compute.refresh_from_db()
        self.assertEqual(compute.status_message, SAMLLMHostQueuedMessage.RECONCILE.value)
        self.assertIsNone(compute.last_reconciled_at)

    def test_deleting_a_compute_queues_its_node_group_deletion(self):
        """The pre_delete receiver queues the node group's deletion by name, however the compute is deleted."""
        compute = self.own_compute("test_queue_delete_compute")
        compute.nodegroup_status = LLMHostComputeNodeGroupStatus.ACTIVE
        compute.save(update_fields=["nodegroup_status"])
        nodegroup_name = compute.nodegroup_name
        absent = self.own_compute("test_queue_delete_absent")
        with self.holding_queued_tasks() as queued:
            compute.delete()
            absent.delete()
        queued["delete_llmhost_nodegroup"].assert_called_once_with(nodegroup_name)
        self.assertEqual(self.nodegroups.deleted, [])

    def test_admin_reconcile_action(self):
        compute = self.own_compute("test_queue_admin_reconcile")
        admin = LLMHostComputeAdmin(LLMHostCompute, MagicMock())
        admin.message_user = MagicMock()  # type: ignore[method-assign]
        request = MagicMock()
        with self.holding_queued_tasks() as queued:
            admin.reconcile(request, LLMHostCompute.objects.filter(pk=compute.pk))
        queued["reconcile_llmhost_compute"].assert_called_once_with(compute.pk)
        admin.message_user.assert_called_once_with(request, f"{compute}: {SAMLLMHostQueuedMessage.RECONCILE.value}")
