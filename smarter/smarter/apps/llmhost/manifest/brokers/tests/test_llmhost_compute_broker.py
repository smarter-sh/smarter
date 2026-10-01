# pylint: disable=wrong-import-position
"""Test SAMLLMHostComputeBroker."""

import os
from decimal import Decimal

from smarter.apps.llmhost.manifest.brokers.llmhost_compute import (
    SAMLLMHostComputeBroker,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.model import (
    SAMLLMHostCompute,
)
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.services.cluster import (
    InMemoryClusterBackend,
    configure_cluster,
)
from smarter.apps.llmhost.services.nodegroups import (
    InMemoryNodeGroupBackend,
    configure_nodegroups,
    get_nodegroups,
)
from smarter.apps.llmhost.tests.base_classes import (
    ensure_builtin_computes,
    get_test_data,
)
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)

COMPUTE_NAME = "test_broker_compute"


# pylint: disable=too-many-public-methods
class TestSmarterLLMHostComputeBroker(TestSAMBrokerBaseClass):
    """Test the Smarter SAMLLMHostComputeBroker, with in-memory node groups."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cluster = InMemoryClusterBackend(namespace="smarter-platform-test")
        configure_cluster(lambda: cls.cluster)
        cls.nodegroups = InMemoryNodeGroupBackend()
        configure_nodegroups(lambda: cls.nodegroups)
        # a safety net: tests must never create real node groups.
        assert isinstance(get_nodegroups(), InMemoryNodeGroupBackend)
        ensure_builtin_computes()

    @classmethod
    def tearDownClass(cls):
        LLMHost.objects.filter(user_profile__account=cls.account).delete()
        LLMHostCompute.objects.filter(user_profile__account=cls.account).delete()
        configure_cluster(None)
        configure_nodegroups(None)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("llmhost_compute.yaml")
        self.cluster.resources.clear()
        self.nodegroups.nodegroups.clear()
        self.nodegroups.created.clear()
        self.nodegroups.deleted.clear()
        self.addCleanup(LLMHostCompute.objects.filter(user_profile=self.user_profile).delete)
        self.addCleanup(LLMHost.objects.filter(user_profile=self.user_profile).delete)

    @property
    def SAMBrokerClass(self) -> type[SAMLLMHostComputeBroker]:
        return SAMLLMHostComputeBroker

    @property
    def broker(self) -> SAMLLMHostComputeBroker:
        return super().broker  # type: ignore

    def fresh_broker(self, manifest: str = "") -> SAMLLMHostComputeBroker:
        """A new broker for the test manifest, or another, without cached state."""
        if not manifest:
            with open(self.manifest_filespec, encoding="utf-8") as f:
                manifest = f.read()
        return SAMLLMHostComputeBroker(request=self.request, loader=SAMLoader(manifest=manifest))

    def compute(self) -> LLMHostCompute:
        return LLMHostCompute.objects.get(user_profile=self.user_profile, name=COMPUTE_NAME)

    def data(self, response) -> dict:
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        return json.loads(response.content)["data"]

    def changed_manifest(self, **spec_changes) -> str:
        """The test manifest, with parts of its spec replaced, as json, which the loader reads."""
        manifest = get_test_data(self.manifest_filespec)
        for block, value in spec_changes.items():
            manifest["spec"][block] = value
        return json.dumps(manifest)

    def test_broker_initialization(self):
        """Test the broker's kind and model classes, and that it creates nothing lazily."""
        self.assertTrue(self.ready)
        self.assertEqual(self.broker.kind, "LLMHostCompute")
        self.assertIs(self.broker.ORMModelClass, LLMHostCompute)
        self.assertIsInstance(self.broker.manifest, SAMLLMHostCompute)
        self.assertIsNone(self.broker.compute)

    def test_example_manifest(self):
        """Test that example_manifest() returns a valid manifest."""
        SAMLLMHostCompute(**self.data(self.broker.example_manifest(self.request)))

    def test_apply(self):
        """Test that apply() creates the LLMHostCompute, with its spec and the copied fields, and no node group."""
        self.data(self.broker.apply(self.request, **self.kwargs))
        compute = self.compute()
        self.assertEqual((compute.instance_type, compute.cpu, compute.memory_gb), ("g6.2xlarge", 8, 32))
        self.assertEqual((compute.gpu_type, compute.gpu_count, compute.gpu_memory_gb), ("L4", 1, 24))
        self.assertEqual((compute.max_nodes, compute.price_per_hour), (2, Decimal("0.9776")))
        self.assertEqual(compute.spec["node"]["diskSizeGb"], 100)
        self.assertEqual(compute.ami_type, "AL2023_x86_64_NVIDIA")
        self.assertEqual(sorted(compute.tags_list), ["gpu", "test"])
        self.assertEqual(compute.nodegroup_status, "absent")
        self.assertEqual(self.nodegroups.created, [])

    def test_apply_updates(self):
        """Test that applying again updates the LLMHostCompute, rather than creating another."""
        self.broker.apply(self.request, **self.kwargs)
        pk = self.compute().pk
        self.fresh_broker(self.changed_manifest(nodeGroup={"maxNodes": 3})).apply(self.request, **self.kwargs)
        self.assertEqual(LLMHostCompute.objects.filter(user_profile=self.user_profile, name=COMPUTE_NAME).count(), 1)
        self.assertEqual((self.compute().pk, self.compute().max_nodes), (pk, 3))

    def test_apply_node_with_nodegroup(self):
        """Test that a node group's nodes cannot change while it exists, but its maximum and cost can."""
        self.broker.apply(self.request, **self.kwargs)
        node = get_test_data(self.manifest_filespec)["spec"]["node"]
        bigger = {**node, "instanceType": "g6.4xlarge", "cpu": 16, "memoryGb": 64}
        # without a node group, the node can change.
        self.fresh_broker(self.changed_manifest(node=bigger)).apply(self.request, **self.kwargs)
        self.assertEqual(self.compute().instance_type, "g6.4xlarge")
        LLMHostCompute.objects.filter(pk=self.compute().pk).update(nodegroup_status="ACTIVE")
        with self.assertRaises(SAMBrokerError):
            self.fresh_broker(self.changed_manifest(node=node)).apply(self.request, **self.kwargs)
        self.assertEqual(self.compute().instance_type, "g6.4xlarge")
        manifest = self.changed_manifest(node=bigger, nodeGroup={"maxNodes": 4}, cost={"perHour": "1.5"})
        self.fresh_broker(manifest).apply(self.request, **self.kwargs)
        self.assertEqual((self.compute().max_nodes, self.compute().price_per_hour), (4, Decimal("1.5")))

    def test_describe(self):
        """Test that describe() round trips the manifest, with the node group's status."""
        self.broker.apply(self.request, **self.kwargs)
        data = self.data(self.fresh_broker().describe(self.request, **self.kwargs))
        manifest = SAMLLMHostCompute(**data)
        self.assertEqual(manifest.metadata.name, COMPUTE_NAME)
        self.assertEqual(manifest.spec.node.gpu.type, "L4")  # type: ignore[union-attr]
        status = data["status"]
        self.assertEqual((status["nodeGroupStatus"], status["desiredNodes"], status["llmhosts"]), ("absent", 0, 0))
        self.assertEqual(status["nodeGroupName"], self.compute().nodegroup_name)
        self.assertEqual(status["accountNumber"], self.account.account_number)

    def test_get(self):
        """Test that get() returns the user's LLMHostComputes, and the built-in ones."""
        self.broker.apply(self.request, **self.kwargs)
        data = self.data(self.fresh_broker().get(self.request))
        names = [item["name"] for item in data["data"]["items"]]
        self.assertIn(COMPUTE_NAME, names)
        self.assertIn("gpu_l4_1x", names)
        named = self.data(self.fresh_broker().get(self.request, name=COMPUTE_NAME))
        self.assertEqual(named["metadata"]["count"], 1)

    def test_deploy(self):
        """Test that deploy reconciles the node group: no LLMHost uses it, so it is not created."""
        self.broker.apply(self.request, **self.kwargs)
        data = self.data(self.fresh_broker().deploy(self.request, **self.kwargs))
        self.assertEqual((data["needed"], data["desired"], data["nodegroup_status"]), (0, 0, "absent"))
        self.assertEqual(self.nodegroups.created, [])
        self.assertIsNotNone(self.compute().last_reconciled_at)

    def test_deploy_error(self):
        """Test that a node group error is a broker error."""
        self.broker.apply(self.request, **self.kwargs)
        self.nodegroups.fail = "AWS is down"
        self.addCleanup(setattr, self.nodegroups, "fail", None)
        with self.assertRaises(SAMBrokerError):
            self.fresh_broker().deploy(self.request, **self.kwargs)

    def test_delete(self):
        """Test that delete() deletes the LLMHostCompute and its node group."""
        self.broker.apply(self.request, **self.kwargs)
        compute = self.compute()
        self.nodegroups.create(compute, 0)
        LLMHostCompute.objects.filter(pk=compute.pk).update(nodegroup_status="ACTIVE")
        self.assertTrue(
            self.validate_smarter_journaled_json_response_ok(self.fresh_broker().delete(self.request, **self.kwargs))
        )
        self.assertFalse(LLMHostCompute.objects.filter(pk=compute.pk).exists())
        self.assertEqual(self.nodegroups.deleted, [compute.nodegroup_name])

    def test_delete_in_use(self):
        """Test that an LLMHostCompute that LLMHosts use cannot be deleted."""
        self.broker.apply(self.request, **self.kwargs)
        compute = self.compute()
        LLMHost.objects.create(name="test_broker_compute_llmhost", user_profile=self.user_profile, compute=compute)
        with self.assertRaises(SAMBrokerError):
            self.fresh_broker().delete(self.request, **self.kwargs)
        self.assertTrue(LLMHostCompute.objects.filter(pk=compute.pk).exists())

    def test_not_found(self):
        """Test that commands on an LLMHostCompute that does not exist raise not found."""
        for command in ("describe", "delete", "deploy"):
            with self.subTest(command=command):
                with self.assertRaises(SAMBrokerErrorNotFound):
                    getattr(self.fresh_broker(), command)(self.request, **self.kwargs)

    def test_not_implemented(self):
        for command in ("prompt", "undeploy", "logs"):
            with self.subTest(command=command):
                with self.assertRaises(SAMBrokerErrorNotImplemented):
                    getattr(self.broker, command)(self.request, **self.kwargs)
