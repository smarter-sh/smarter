"""Test the Celery tasks: :mod:`smarter.apps.llmhost.tasks`.

They are called directly, i.e. synchronously.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.utils import timezone

from smarter.apps.account.models import Charge, ChargeTypes
from smarter.apps.llmhost import tasks
from smarter.apps.llmhost.const import (
    RECONCILE_INTERVAL_SECONDS,
    RECONCILE_MAX_ATTEMPTS,
)
from smarter.apps.llmhost.models import LLMHostCompute
from smarter.apps.llmhost.tasks import (
    charge_llmhost_computes,
    destroy_llmhost,
    launch_llmhost,
    managed_hostname,
    reconcile_llmhost_compute,
    reconcile_llmhost_computes,
    refresh_llmhost_status,
)

from .base_classes import LLMHostTestBase


class TestLLMHostTasks(LLMHostTestBase):
    """Test launch_llmhost, destroy_llmhost, refresh_llmhost_status, the compute reconciles, and DNS records."""

    def setUp(self):
        super().setUp()
        # Celery is not eager in tests: a queued task would reach the live worker.
        patcher = patch.object(tasks.reconcile_llmhost_compute, "apply_async")
        self.queued = patcher.start()
        self.addCleanup(patcher.stop)

    def test_launch_and_destroy(self):
        """Test that launch and destroy each queue a reconcile of the compute, which follows its node group."""
        llmhost = self.new_llmhost("test_tasks_launch")
        self.assertEqual(launch_llmhost(llmhost.pk), "provisioning")
        self.assertIsNotNone(self.cluster.get("deployment", self.base_name(llmhost)))
        llmhost.refresh_from_db()
        self.queued.assert_called_once_with((llmhost.compute.pk,), countdown=RECONCILE_INTERVAL_SECONDS)
        self.assertEqual(destroy_llmhost(llmhost.pk, purge=True), "inactive")
        self.assertEqual(self.cluster.resources, {})
        self.assertEqual(self.queued.call_count, 2)

    def test_reconcile_compute(self):
        """Test that a reconcile queues another until the node group is settled, and checks the LLMHosts' status."""
        llmhost = self.new_llmhost("test_tasks_reconcile")
        launch_llmhost(llmhost.pk)
        llmhost.refresh_from_db()
        compute = llmhost.compute
        self.queued.reset_mock()
        state = reconcile_llmhost_compute(compute.pk)
        self.assertEqual((state["needed"], state["desired"], state["ready"]), (1, 1, 0))
        self.queued.assert_called_once_with((compute.pk, 2), countdown=RECONCILE_INTERVAL_SECONDS)
        # the node joins: the node group is settled, and the LLMHost waits only for its pods.
        self.join_nodes(compute)
        self.queued.reset_mock()
        state = reconcile_llmhost_compute(compute.pk, attempt=2)
        self.assertEqual(state["ready"], 1)
        self.queued.assert_not_called()
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status, "pending")
        # it gives up after RECONCILE_MAX_ATTEMPTS, and Celery Beat's reconcile takes over.
        self.nodegroups.fail = "AWS is down"
        self.assertIsNone(reconcile_llmhost_compute(compute.pk, attempt=RECONCILE_MAX_ATTEMPTS))
        self.queued.assert_not_called()
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
        compute = llmhost.compute
        self.assertIn(compute.name, reconcile_llmhost_computes())
        llmhost.status = "inactive"
        llmhost.save(update_fields=["status"])
        messages = reconcile_llmhost_computes()
        self.assertIn(compute.name, messages)
        self.assertEqual(len(self.nodegroups.removed), 1)

    def test_missing(self):
        self.assertIsNone(launch_llmhost(0))
        self.assertIsNone(destroy_llmhost(0))

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
        self.assertTrue(managed_hostname(llmhost).startswith(self.base_name(llmhost)))
        custom = self.new_llmhost("test_tasks_custom_host", network={"hostname": "llm.example.com"})
        self.assertIsNone(managed_hostname(custom))
        internal = self.new_llmhost("test_tasks_internal", network={"ingress": False})
        self.assertIsNone(managed_hostname(internal))

    def test_dns_records(self):
        """Test that DNS records are created and destroyed when DNS is enabled."""
        llmhost = self.new_llmhost("test_tasks_dns")
        route53 = MagicMock()
        with (
            patch.object(tasks, "dns_enabled", return_value=True),
            patch("smarter.common.helpers.aws_helpers.aws_helper") as aws_helper,
            patch("smarter.apps.llmclient.tasks.destroy_domain_a_record.destroy_domain_A_record") as destroy_task,
        ):
            aws_helper.route53 = route53
            tasks.create_dns_record(llmhost)
            route53.create_domain_a_record.assert_called_once()
            self.assertEqual(route53.create_domain_a_record.call_args.kwargs["hostname"], managed_hostname(llmhost))
            tasks.destroy_dns_record(llmhost)
            destroy_task.delay.assert_called_once()
        # disabled by the test base class.
        route53.reset_mock()
        tasks.create_dns_record(llmhost)
        route53.create_domain_a_record.assert_not_called()
