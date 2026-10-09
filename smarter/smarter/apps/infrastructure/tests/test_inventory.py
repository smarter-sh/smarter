"""
Test :mod:`smarter.apps.infrastructure.services.inventory`, its Celery task and its management command.

The cloud is the in-memory provider, and the cluster is :class:`FakeKubernetes`, which answers
:meth:`~smarter.apps.infrastructure.services.kubernetes.KubernetesService.find_resources` from a
dict, so nothing reaches real infrastructure.
"""

from io import StringIO
from typing import Optional
from unittest.mock import patch

from django.core.management import call_command

from smarter.apps.infrastructure.const import KubernetesResourceTypes
from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.services import KubernetesService, configure_kubernetes
from smarter.apps.infrastructure.services.base import DiscoveredResource
from smarter.apps.infrastructure.services.inventory import (
    KUBERNETES_SOURCES,
    discover,
    sync_inventory,
)
from smarter.apps.infrastructure.signals import (
    billable_resource_created,
    billable_resource_destroyed,
    resource_created,
    resource_destroyed,
)
from smarter.apps.infrastructure.tasks import sync_infrastructure_inventory
from smarter.common.conf import smarter_settings

from .base import InfrastructureTestBase

MODULE = "smarter.apps.infrastructure.services.inventory"
COMMAND = "smarter.apps.infrastructure.management.commands.sync_infrastructure_inventory"
ENV = smarter_settings.environment_namespace
OTHER = "smarter-platform-other"


class FakeKubernetes(KubernetesService):
    """A cluster whose resources are a dict of items, keyed by kind.

    A kind that is missing cannot be listed.
    """

    def __init__(self, provider_name: str):
        super().__init__(provider_name=provider_name)
        self.items: dict[str, list[dict]] = {}
        self.calls: list[tuple[str, Optional[str]]] = []

    @property
    def ready(self) -> bool:
        return True

    def find_resources(self, kind, namespace=None):
        self.calls.append((kind, namespace))
        items = self.items.get(kind)
        if items is None or namespace is None:
            return items
        return [i for i in items if i["metadata"]["namespace"] == namespace]

    def apply_manifest(self, manifest):
        raise NotImplementedError

    def get_resource(self, kind, name, namespace):
        raise NotImplementedError

    def list_resources(self, kind, namespace, selector=None):
        raise NotImplementedError

    def delete_resource(self, kind, name, namespace):
        raise NotImplementedError

    def delete_resources(self, kinds, namespace, selector):
        raise NotImplementedError

    def get_pod_logs(self, namespace, selector, container=None, tail=200):
        raise NotImplementedError


def item(name: str, namespace: str = "", spec: Optional[dict] = None, status: Optional[dict] = None) -> dict:
    return {"metadata": {"name": name, "namespace": namespace}, "spec": spec or {}, "status": status or {}}


def load_balanced(hostname: str = "", ip: str = "") -> dict:
    return {"loadBalancer": {"ingress": [{"hostname": hostname, "ip": ip}]}}


class InventoryTestBase(InfrastructureTestBase):
    """An in-memory provider with an EKS-like cluster, and a fake cluster with a resource of each kind."""

    def setUp(self):
        super().setUp()
        self.provider.cluster_resources = {
            str(KubernetesResourceTypes.CLUSTER): [
                DiscoveredResource(str(KubernetesResourceTypes.CLUSTER), "cluster", "arn:cluster", billable=True)
            ],
            str(KubernetesResourceTypes.ADDON): [
                DiscoveredResource(str(KubernetesResourceTypes.ADDON), "coredns", "arn:addon/coredns")
            ],
            str(KubernetesResourceTypes.NODEGROUP): [
                DiscoveredResource(str(KubernetesResourceTypes.NODEGROUP), "default", "arn:nodegroup/default")
            ],
        }
        self.kubernetes = FakeKubernetes(self.provider.provider_name)
        configure_kubernetes(lambda: self.kubernetes)
        self.kubernetes.items = {
            "node": [item("node-1", spec={"providerID": "aws:///us-east-1a/i-1"}), item("")],
            "persistentvolume": [
                item("pv-csi", spec={"csi": {"volumeHandle": "vol-1"}, "claimRef": {"namespace": ENV}}),
                item("pv-ebs", spec={"awsElasticBlockStore": {"volumeID": "vol-2"}, "claimRef": {"namespace": ENV}}),
                item("pv-other", spec={"csi": {"volumeHandle": "vol-3"}, "claimRef": {"namespace": OTHER}}),
                item("pv-unbound", spec={"csi": {"volumeHandle": "vol-4"}}),
            ],
            "service": [
                item("qdrant", ENV, {"type": "LoadBalancer"}, load_balanced(hostname="nlb.aws")),
                item("api", ENV, {"type": "ClusterIP"}),
                item("ingress-nginx", OTHER, {"type": "LoadBalancer"}, load_balanced(hostname="other.aws")),
            ],
            "ingress": [
                item("app.example.com", ENV, status=load_balanced(ip="10.0.0.1")),
                item("other.example.com", OTHER),
            ],
            "certificate": [
                item("app.example.com-tls", ENV, spec={"secretName": "app.example.com-tls"}),
                item("other.example.com-tls", OTHER),
            ],
        }

    def active(self, resource_type: KubernetesResourceTypes) -> dict[str, InfrastructureResource]:
        return {
            row.resource_name: row
            for row in InfrastructureResource.objects.filter(
                provider=self.provider.provider_name,
                resource_type=str(resource_type),
                status=InfrastructureResource.Status.ACTIVE,
            )
        }


class TestDiscover(InventoryTestBase):
    """Test what the inventory discovers."""

    def test_discover(self):
        resources = discover()
        self.assertEqual(set(resources), {str(t) for t in KubernetesResourceTypes})
        by_type = {t: {r.resource_name: r for r in rs} for t, rs in resources.items()}
        self.assertEqual(list(by_type["kubernetes.node"]), ["node-1"])
        self.assertEqual(by_type["kubernetes.node"]["node-1"].resource_id, "aws:///us-east-1a/i-1")
        self.assertTrue(by_type["kubernetes.node"]["node-1"].billable)
        self.assertEqual(set(by_type["kubernetes.persistentvolume"]), {"pv-csi", "pv-ebs"})
        self.assertEqual(by_type["kubernetes.persistentvolume"]["pv-csi"].resource_id, "vol-1")
        self.assertEqual(by_type["kubernetes.persistentvolume"]["pv-ebs"].resource_id, "vol-2")
        self.assertEqual(list(by_type["kubernetes.loadbalancer"]), ["qdrant"])
        self.assertEqual(by_type["kubernetes.loadbalancer"]["qdrant"].resource_id, "nlb.aws")
        self.assertEqual(list(by_type["kubernetes.ingress"]), ["app.example.com"])
        self.assertEqual(list(by_type["kubernetes.certificate"]), ["app.example.com-tls"])
        self.assertEqual(by_type["kubernetes.ingress"]["app.example.com"].resource_id, "10.0.0.1")
        self.assertFalse(by_type["kubernetes.ingress"]["app.example.com"].billable)
        self.assertEqual(by_type["kubernetes.certificate"]["app.example.com-tls"].resource_id, "app.example.com-tls")
        self.assertIn(("node", None), self.kubernetes.calls)
        self.assertIn(("persistentvolume", None), self.kubernetes.calls)
        self.assertIn(("service", ENV), self.kubernetes.calls)
        self.assertIn(("ingress", ENV), self.kubernetes.calls)
        self.assertIn(("certificate", ENV), self.kubernetes.calls)
        self.assertEqual(len(self.kubernetes.calls), len(KUBERNETES_SOURCES))

    def test_unlisted_kinds_are_left_out(self):
        """A kind that cannot be listed, e.g. without the cert-manager CRD, is left out, not empty."""
        del self.kubernetes.items["certificate"]
        self.kubernetes.items["ingress"] = []
        resources = discover()
        self.assertNotIn("kubernetes.certificate", resources)
        self.assertEqual(resources["kubernetes.ingress"], [])

    def test_provider_not_ready(self):
        self.provider.ready = False
        resources = discover()
        self.assertNotIn("kubernetes.cluster", resources)
        self.assertIn("kubernetes.node", resources)

    def test_failures_are_logged(self):
        with (
            patch.object(self.provider, "get_kubernetes_cluster_resources", side_effect=RuntimeError("boom")),
            patch.object(self.kubernetes, "find_resources", side_effect=RuntimeError("boom")),
            patch(f"{MODULE}.logger") as logger,
        ):
            self.assertEqual(discover(), {})
        self.assertEqual(logger.warning.call_count, 1 + len(KUBERNETES_SOURCES))

    def test_base_service_cannot_list(self):
        """The base class's find_resources() tells the inventory that nothing could be listed."""
        self.assertIsNone(KubernetesService.find_resources(self.kubernetes, "node"))


class TestSyncInventory(InventoryTestBase):
    """Test that the ledger is reconciled with what exists."""

    def test_sync_records_what_exists(self):
        events = self.capture(billable_resource_created, resource_created)
        results = sync_inventory()
        self.assertEqual(results["kubernetes.node"], {"found": 1, "created": 1, "destroyed": 0})
        self.assertEqual(results["kubernetes.persistentvolume"]["created"], 2)
        self.assertEqual(self.active(KubernetesResourceTypes.CLUSTER)["cluster"].resource_id, "arn:cluster")
        self.assertTrue(self.active(KubernetesResourceTypes.CLUSTER)["cluster"].billable)
        self.assertFalse(self.active(KubernetesResourceTypes.ADDON)["coredns"].billable)
        self.assertEqual(self.active(KubernetesResourceTypes.NODE)["node-1"].service, "kubernetes")
        billable = {e["resource_type"] for e in self.sent(events, billable_resource_created)}
        free = {e["resource_type"] for e in self.sent(events, resource_created)}
        self.assertEqual(
            billable,
            {"kubernetes.cluster", "kubernetes.node", "kubernetes.persistentvolume", "kubernetes.loadbalancer"},
        )
        self.assertEqual(
            free, {"kubernetes.addon", "kubernetes.nodegroup", "kubernetes.ingress", "kubernetes.certificate"}
        )

    def test_sync_is_idempotent(self):
        sync_inventory()
        events = self.capture(billable_resource_created, resource_created)
        results = sync_inventory()
        self.assertTrue(all(r["created"] == 0 and r["destroyed"] == 0 for r in results.values()))
        self.assertEqual(events, [])

    def test_sync_records_what_was_destroyed(self):
        sync_inventory()
        events = self.capture(billable_resource_destroyed, resource_destroyed)
        self.kubernetes.items["node"] = [item("node-2", spec={"providerID": "aws:///us-east-1a/i-2"})]
        self.kubernetes.items["ingress"] = []
        results = sync_inventory()
        self.assertEqual(results["kubernetes.node"], {"found": 1, "created": 1, "destroyed": 1})
        self.assertEqual(results["kubernetes.ingress"], {"found": 0, "created": 0, "destroyed": 1})
        self.assertEqual(list(self.active(KubernetesResourceTypes.NODE)), ["node-2"])
        destroyed = InfrastructureResource.objects.get(
            resource_type="kubernetes.node", resource_name="node-1", status=InfrastructureResource.Status.DESTROYED
        )
        self.assertIsNotNone(destroyed.destroyed_at)
        self.assertEqual(self.sent(events, billable_resource_destroyed)[0]["resource_id"], "aws:///us-east-1a/i-1")
        self.assertEqual(self.sent(events, resource_destroyed)[0]["resource_name"], "app.example.com")

    def test_unlisted_kinds_are_not_destroyed(self):
        """An unavailable cluster is not mistaken for an empty one."""
        sync_inventory()
        self.kubernetes.items = {}
        self.provider.ready = False
        self.assertEqual(sync_inventory(), {})
        self.assertIn("node-1", self.active(KubernetesResourceTypes.NODE))
        self.assertIn("cluster", self.active(KubernetesResourceTypes.CLUSTER))

    def test_resource_id_is_updated(self):
        """A resource that the services recorded by name gets its cloud id, e.g. an Ingress's load balancer."""
        InfrastructureResource.record_created(
            provider=self.provider.provider_name,
            service="kubernetes",
            resource_type="kubernetes.ingress",
            resource_name="app.example.com",
            resource_id="app.example.com",
        )
        results = sync_inventory()
        self.assertEqual(results["kubernetes.ingress"]["created"], 0)
        self.assertEqual(self.active(KubernetesResourceTypes.INGRESS)["app.example.com"].resource_id, "10.0.0.1")


class TestSyncInventoryTask(InventoryTestBase):
    """Test the Celery task, called directly, so that it never reaches a worker."""

    def test_task(self):
        results = sync_infrastructure_inventory()
        self.assertEqual(results["kubernetes.cluster"]["created"], 1)
        self.assertIn("node-1", self.active(KubernetesResourceTypes.NODE))


class TestSyncInventoryCommand(InventoryTestBase):
    """Test manage.py sync_infrastructure_inventory."""

    def test_command(self):
        stdout = StringIO()
        call_command("sync_infrastructure_inventory", stdout=stdout)
        self.assertIn("kubernetes.node: 1 found, 1 created, 0 destroyed", stdout.getvalue())
        self.assertIn("node-1", self.active(KubernetesResourceTypes.NODE))

    def test_nothing_listed(self):
        stdout = StringIO()
        with patch(f"{COMMAND}.sync_inventory", return_value={}):
            call_command("sync_infrastructure_inventory", stdout=stdout)
        self.assertIn("Nothing could be listed", stdout.getvalue())

    def test_failure(self):
        with patch(f"{COMMAND}.sync_inventory", side_effect=RuntimeError("boom")):
            with self.assertRaises(SystemExit):
                call_command("sync_infrastructure_inventory", stdout=StringIO())
