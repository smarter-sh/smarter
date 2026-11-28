"""Test the Celery tasks: :mod:`smarter.apps.llmhost.tasks.llmhost`, :mod:`~smarter.apps.llmhost.tasks.compute` and :mod:`~smarter.apps.llmhost.tasks.dns`.

They are called directly, i.e. synchronously.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.utils import timezone

from smarter.apps.account.models import Charge, ChargeTypes
from smarter.apps.llmclient.tasks.destroy_domain_a_record import (
    destroy_domain_A_record,
)
from smarter.apps.llmhost import tasks
from smarter.apps.llmhost.const import (
    RECONCILE_INTERVAL_SECONDS,
    RECONCILE_MAX_ATTEMPTS,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostEventType
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute, LLMHostEvent
from smarter.apps.llmhost.services.compute import builtin_computes
from smarter.apps.llmhost.tasks import (
    charge_llmhost_computes,
    delete_llmhost,
    delete_llmhost_nodegroup,
    destroy_llmhost,
    launch_llmhost,
    managed_hostname,
    reconcile_llmhost_compute,
    reconcile_llmhost_computes,
    refresh_llmhost_status,
)
from smarter.lib.typing import required

from .base_classes import LLMHostTestBase


class TestLLMHostTasks(LLMHostTestBase):
    """
    Test the llmhost tasks, called directly, and DNS records.

    The reconcile that a task queues is recorded in :attr:`requeued`, never sent: see
    :class:`~smarter.apps.llmhost.tests.base_classes.InMemoryLLMHostInfrastructureMixin`.
    """

    def test_launch_and_destroy(self):
        """Test that launch and destroy each queue a reconcile of the compute, which follows its node group."""
        llmhost = self.new_llmhost("test_tasks_launch")
        self.assertEqual(launch_llmhost(llmhost.pk), "provisioning")
        self.assertIsNotNone(self.cluster.get("deployment", self.base_name(llmhost)))
        llmhost.refresh_from_db()
        compute = required(llmhost.compute, "llmhost.compute")
        self.requeued.assert_called_once_with((compute.pk,), countdown=RECONCILE_INTERVAL_SECONDS)
        self.assertEqual(destroy_llmhost(llmhost.pk, purge=True), "inactive")
        self.assertEqual(self.cluster.resources, {})
        self.assertEqual(self.requeued.call_count, 2)

    def test_reconcile_compute(self):
        """Test that a reconcile queues another until the node group is settled, and checks the LLMHosts' status."""
        llmhost = self.new_llmhost("test_tasks_reconcile")
        launch_llmhost(llmhost.pk)
        llmhost.refresh_from_db()
        compute = required(llmhost.compute, "llmhost.compute")
        self.requeued.reset_mock()
        state = reconcile_llmhost_compute(compute.pk)
        self.assertEqual((state["needed"], state["desired"], state["ready"]), (1, 1, 0))
        self.requeued.assert_called_once_with((compute.pk, 2), countdown=RECONCILE_INTERVAL_SECONDS)
        # the node joins: the node group is settled, and the LLMHost waits only for its pods.
        self.join_nodes(compute)
        self.requeued.reset_mock()
        state = reconcile_llmhost_compute(compute.pk, attempt=2)
        self.assertEqual(state["ready"], 1)
        self.requeued.assert_not_called()
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status, "pending")
        # it gives up after RECONCILE_MAX_ATTEMPTS, and Celery Beat's reconcile takes over.
        self.nodegroups.fail = "AWS is down"
        self.assertIsNone(reconcile_llmhost_compute(compute.pk, attempt=RECONCILE_MAX_ATTEMPTS))
        self.requeued.assert_not_called()
        self.assertIsNone(reconcile_llmhost_compute(0))

    def test_charge_llmhost_computes(self):
        """Test that an hour of a compute's ready nodes is charged to the compute, its owner, and their account."""
        started = timezone.now()
        llmhost = self.new_llmhost("test_tasks_charge")
        compute = llmhost.compute
        price_per_hour = compute.price_per_hour  # type: ignore[union-attr]
        LLMHostCompute.objects.filter(pk=compute.pk).update(ready_nodes=2, price_per_hour=Decimal("1.25"))  # type: ignore[union-attr]
        self.addCleanup(
            LLMHostCompute.objects.filter(pk=compute.pk).update, ready_nodes=0, price_per_hour=price_per_hour  # type: ignore[union-attr]
        )
        charges = Charge.objects.filter(charge_type=ChargeTypes.COMPUTE.value, created_at__gte=started)
        self.addCleanup(charges.delete)
        self.assertEqual(Decimal(charge_llmhost_computes()[compute.name]), Decimal("2.50"))  # type: ignore[union-attr]
        compute.refresh_from_db()  # type: ignore[union-attr]
        locators = [compute.record_locator, compute.user_profile.record_locator, compute.user_profile.account.record_locator]  # type: ignore[union-attr]
        for locator in locators:
            self.assertEqual(charges.get(resource_locator=locator).total_cost, Decimal("2.50"))

    def test_reconcile_computes(self):
        """Test that Celery Beat's reconcile removes the node of a destroyed LLMHost."""
        llmhost = self.new_llmhost("test_tasks_reconcile_all")
        self.launch(llmhost)
        llmhost.refresh_from_db()
        compute = required(llmhost.compute, "llmhost.compute")
        self.assertIn(compute.name, reconcile_llmhost_computes())
        llmhost.status = "inactive"
        llmhost.save(update_fields=["status"])
        messages = reconcile_llmhost_computes()
        self.assertIn(compute.name, messages)
        self.assertEqual(len(self.nodegroups.removed), 1)

    def test_missing(self):
        self.assertIsNone(launch_llmhost(0))
        self.assertIsNone(destroy_llmhost(0))
        self.assertFalse(delete_llmhost(0))

    def test_launch_failure_is_recorded(self):
        """A launch that fails after it was queued, e.g. a Secret deleted since, is the LLMHost's message and event."""
        llmhost = self.new_llmhost("test_tasks_launch_failed", model={"tokenSecret": "test_llmhost_deleted_since"})
        self.assertEqual(launch_llmhost(llmhost.pk), llmhost.status)
        llmhost.refresh_from_db()
        self.assertTrue(llmhost.status_message.startswith("Launch failed: "), llmhost.status_message)
        self.assertIn("test_llmhost_deleted_since", llmhost.status_message)
        error = LLMHostEvent.objects.filter(llmhost=llmhost, event_type=SAMLLMHostEventType.ERROR.value).first()
        self.assertIsNotNone(error)
        self.assertEqual(self.cluster.applied, [])
        self.requeued.assert_not_called()

    def test_destroy_failure_is_recorded(self):
        llmhost = self.new_llmhost("test_tasks_destroy_failed")
        launch_llmhost(llmhost.pk)
        self.cluster.ready = False
        destroy_llmhost(llmhost.pk)
        llmhost.refresh_from_db()
        self.assertTrue(llmhost.status_message.startswith("Undeploy failed: "), llmhost.status_message)
        self.assertNotEqual(self.cluster.resources, {})

    def test_delete_llmhost(self):
        """The task destroys the resources, including the model volume, deletes the LLMHost, and reconciles its compute."""
        llmhost = self.new_llmhost("test_tasks_delete")
        launch_llmhost(llmhost.pk)
        llmhost.refresh_from_db()
        compute = required(llmhost.compute, "llmhost.compute")
        self.requeued.reset_mock()
        self.assertTrue(delete_llmhost(llmhost.pk))
        self.assertFalse(LLMHost.objects.filter(pk=llmhost.pk).exists())
        self.assertEqual(self.cluster.resources, {})
        self.requeued.assert_called_once_with((compute.pk,), countdown=RECONCILE_INTERVAL_SECONDS)

    def test_delete_failure_keeps_the_llmhost(self):
        """A deployed LLMHost whose cluster can't be reached is kept, with why, so that it can be deleted again."""
        llmhost = self.new_llmhost("test_tasks_delete_failed")
        launch_llmhost(llmhost.pk)
        self.cluster.ready = False
        self.assertFalse(delete_llmhost(llmhost.pk))
        llmhost.refresh_from_db()
        self.assertTrue(llmhost.status_message.startswith("Delete failed: "), llmhost.status_message)

    def test_delete_llmhost_nodegroup(self):
        """The node group is deleted by name; a cloud error is logged, and the task reports it."""
        compute = builtin_computes().first()
        assert compute is not None
        self.nodegroups.create(compute, 0)
        self.assertTrue(delete_llmhost_nodegroup(compute.nodegroup_name))
        self.assertEqual(self.nodegroups.deleted, [compute.nodegroup_name])
        self.assertNotIn(compute.nodegroup_name, self.nodegroups.nodegroups)
        self.nodegroups.fail = "AWS is down"
        with self.assertLogs("smarter.apps.llmhost.tasks.compute", level="ERROR") as logs:
            self.assertFalse(delete_llmhost_nodegroup(compute.nodegroup_name))
        self.assertIn("AWS is down", logs.output[0])

    def test_task_names_are_kept(self):
        """Each task keeps the name that Celery Beat's schedule, and messages already queued, use."""
        for task in (
            launch_llmhost,
            destroy_llmhost,
            delete_llmhost,
            delete_llmhost_nodegroup,
            tasks.refresh_llmhost_status,
            tasks.reconcile_llmhost_compute,
            tasks.reconcile_llmhost_computes,
            tasks.charge_llmhost_computes,
        ):
            with self.subTest(task=task.name):
                self.assertTrue(task.name.startswith("smarter.apps.llmhost.tasks."))
                self.assertEqual(task.name.count("."), 4)

    def test_refresh(self):
        """Test that refresh checks one LLMHost, or every deployed LLMHost."""
        deployed = self.new_llmhost("test_tasks_refresh")
        undeployed = self.new_llmhost("test_tasks_refresh_idle")
        self.launch(deployed)
        self.simulate_ready(deployed)
        statuses = refresh_llmhost_status()
        self.assertEqual(statuses.get(deployed.name), "active")
        self.assertNotIn(undeployed.name, statuses)
        self.assertEqual(refresh_llmhost_status(undeployed.pk), {undeployed.name: "inactive"})
        self.cluster.ready = False
        self.assertEqual(refresh_llmhost_status(), {})

    def test_managed_hostname(self):
        """Test that only the default hostname of an Ingress is managed."""
        llmhost = self.new_llmhost("test_tasks_hostname")
        self.assertTrue(required(managed_hostname(llmhost), "managed_hostname").startswith(self.base_name(llmhost)))
        custom = self.new_llmhost("test_tasks_custom_host", network={"hostname": "llm.example.com"})
        self.assertIsNone(managed_hostname(custom))
        internal = self.new_llmhost("test_tasks_internal", network={"ingress": False})
        self.assertIsNone(managed_hostname(internal))

    def test_dns_records(self):
        """Test that DNS records are created and destroyed when DNS is enabled."""
        llmhost = self.new_llmhost("test_tasks_dns")
        infrastructure = MagicMock()
        with (
            patch.object(tasks.dns, "dns_enabled", return_value=True),
            patch.object(tasks.dns, "infrastructure", infrastructure),
            # the real task's delay: a MagicMock in place of the task would have a delay even if the task did not.
            patch.object(destroy_domain_A_record, "delay") as delay,
        ):
            tasks.create_dns_record(llmhost)
            infrastructure.dns.create_domain_a_record.assert_called_once()
            self.assertEqual(
                infrastructure.dns.create_domain_a_record.call_args.kwargs["hostname"], managed_hostname(llmhost)
            )
            tasks.destroy_dns_record(llmhost)
            delay.assert_called_once()
            self.assertEqual(delay.call_args.kwargs["hostname"], managed_hostname(llmhost))
        # disabled by the test base class.
        infrastructure.reset_mock()
        with patch.object(tasks.dns, "infrastructure", infrastructure):
            tasks.create_dns_record(llmhost)
        infrastructure.dns.create_domain_a_record.assert_not_called()
