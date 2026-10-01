"""Test the nodes that LLMHosts run on: :mod:`smarter.apps.llmhost.services.compute`."""

from decimal import Decimal

from smarter.apps.llmhost.manifest.brokers.llmhost_compute import (
    compute_spec_to_django_orm,
)
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostSpec
from smarter.apps.llmhost.manifest.models.llmhost_compute.spec import (
    SAMLLMHostComputeSpec,
)
from smarter.apps.llmhost.models import LLMHostCompute
from smarter.apps.llmhost.services.compute import (
    ComputeProvisioner,
    PodRequests,
    choose_compute,
    cost_per_hour,
    cpu_millicores,
    fits,
    memory_mib,
    nodes_needed,
    pod_requests,
    resolve_compute,
)
from smarter.apps.llmhost.services.exceptions import LLMHostComputeError
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import LLMHostTestBase, builtin_compute_models, spec_data


def by_name(name: str) -> LLMHostCompute:
    return next(compute for compute in builtin_compute_models() if compute.name == name)


class TestSizing(SmarterTestBase):
    """Test pod requests, fit, cost and choice against the built-in computes, without a database."""

    def test_quantities(self):
        self.assertEqual((cpu_millicores("4"), cpu_millicores("3500m"), cpu_millicores("0.5")), (4000, 3500, 500))
        self.assertEqual((memory_mib("24Gi"), memory_mib("512Mi"), memory_mib("1G")), (24576, 512, 954))
        with self.assertRaises(LLMHostComputeError):
            memory_mib("lots")

    def test_pod_requests(self):
        pod = pod_requests(SAMLLMHostSpec(**spec_data()))
        self.assertEqual(pod, PodRequests(cpu_millicores=4000, memory_mib=24576, gpus=1, vram_gb=21))

    def test_allocatable(self):
        """Test that a node's allocatable capacity leaves room for the kubelet and DaemonSets."""
        node = by_name("gpu_l4_1x")
        self.assertEqual((node.allocatable_cpu_millicores, node.allocatable_memory_mib), (7340, 30249))
        # a pod that requests all of a 4 vCPU node's CPU does not fit it.
        self.assertTrue(fits(PodRequests(4000, 2048), by_name("cpu_small")))
        self.assertFalse(fits(PodRequests(3000, 2048), by_name("cpu_small")))

    def test_fits(self):
        """Test the reasons that a pod does not fit a node."""
        l4 = by_name("gpu_l4_1x")
        self.assertEqual(fits(PodRequests(4000, 24576, 1, 21), l4), [])
        self.assertIn("GPUs", fits(PodRequests(4000, 24576, 2, 21), l4)[0])
        self.assertIn("GPU memory", fits(PodRequests(4000, 24576, 1, 30), l4)[0])
        self.assertEqual(len(fits(PodRequests(8000, 40960, 0), l4)), 2)

    def test_cost(self):
        """Test that one replica costs its largest share of its node: GPUs, CPU or memory."""
        self.assertEqual(cost_per_hour(PodRequests(4000, 24576, 1), by_name("gpu_l4_1x")), Decimal("0.9776"))
        # 2 of 4 GPUs.
        self.assertEqual(cost_per_hour(PodRequests(6000, 71680, 2), by_name("gpu_l40s_4x")), Decimal("5.2463"))
        self.assertIsNone(cost_per_hour(PodRequests(1000, 1024), None))

    def test_choose(self):
        """Test that the cheapest node that fits is chosen, and a CPU node for a pod without GPUs."""
        computes = builtin_compute_models()
        self.assertEqual(choose_compute(PodRequests(4000, 24576, 1, 21), computes).name, "gpu_l4_1x")
        self.assertEqual(choose_compute(PodRequests(4000, 24576, 1, 40), computes).name, "gpu_l40s_1x")
        self.assertEqual(choose_compute(PodRequests(10000, 178176, 4, 177), computes).name, "gpu_l40s_4x")
        # by the node's price, not the pod's share of it.
        self.assertEqual(choose_compute(PodRequests(2000, 4096), computes).name, "cpu_small")
        self.assertEqual(choose_compute(PodRequests(6000, 4096), computes).name, "cpu_medium")
        with self.assertRaises(LLMHostComputeError):
            choose_compute(PodRequests(4000, 24576, 16, 2000), computes)

    def test_nodes_needed(self):
        """Test that pods are packed onto nodes, first fit, largest first."""
        l40s_4x = by_name("gpu_l40s_4x")
        self.assertEqual(nodes_needed([], l40s_4x), 0)
        self.assertEqual(nodes_needed([PodRequests(4000, 24576, 1)] * 4, l40s_4x), 1)
        self.assertEqual(nodes_needed([PodRequests(4000, 24576, 1)] * 5, l40s_4x), 2)
        self.assertEqual(nodes_needed([PodRequests(4000, 24576, 2)] * 3, l40s_4x), 2)
        # one pod per node, when a node fits one.
        self.assertEqual(nodes_needed([PodRequests(4000, 24576, 1)] * 3, by_name("gpu_l4_1x")), 3)


class TestComputeProvisioner(LLMHostTestBase):
    """Test resolve_compute() and ComputeProvisioner, with in-memory node groups."""

    def setUp(self):
        super().setUp()
        self.provisioner = ComputeProvisioner(cluster=self.cluster, nodegroups=self.nodegroups)

    def own_compute(self, name: str, **node) -> LLMHostCompute:
        """An LLMHostCompute of the test user, deleted when the test ends."""
        spec = SAMLLMHostComputeSpec(
            node={"instanceType": "g6.2xlarge", "cpu": 8, "memoryGb": 32, **node},
            nodeGroup={"maxNodes": 2},
            cost={"perHour": "1.0"},
        )
        compute = LLMHostCompute.objects.create(
            name=name, user_profile=self.user_profile, **compute_spec_to_django_orm(spec)
        )
        self.addCleanup(LLMHostCompute.objects.filter(pk=compute.pk).delete)
        return compute

    def deploy(self, name: str, **overrides):
        """A throwaway LLMHost, as deployed, without launching it."""
        llmhost = self.new_llmhost(name, **overrides)
        llmhost.status = "pending"
        llmhost.save(update_fields=["status"])
        return llmhost

    def test_resolve(self):
        """Test that spec.compute is resolved, or the cheapest that fits is chosen."""
        spec = SAMLLMHostSpec(**spec_data())
        self.assertEqual(resolve_compute(spec, self.user_profile).name, "gpu_a10g_1x")
        auto = SAMLLMHostSpec(**spec_data(compute=None))
        self.assertEqual(resolve_compute(auto, self.user_profile).name, "gpu_l4_1x")
        with self.assertRaises(LLMHostComputeError):
            resolve_compute(SAMLLMHostSpec(**spec_data(compute="gpu_tpu_1x")), self.user_profile)
        with self.assertRaises(LLMHostComputeError):
            resolve_compute(SAMLLMHostSpec(**spec_data(compute="cpu_small")), self.user_profile)

    def test_resolve_own_first(self):
        """Test that the user's own compute is preferred to a built-in one of the same name."""
        own = self.own_compute("gpu_a10g_1x", gpu={"type": "A10G", "count": 1, "memoryGb": 24})
        self.assertEqual(resolve_compute(SAMLLMHostSpec(**spec_data()), self.user_profile).pk, own.pk)

    def test_reconcile_creates_and_scales(self):
        """Test that a node group is created for the nodes that LLMHosts need, and scaled up to max_nodes."""
        compute = self.own_compute("test_compute_scale", gpu={"type": "L4", "count": 1, "memoryGb": 24})
        self.assertEqual(self.provisioner.reconcile(compute).nodegroup_status, "absent")
        self.assertEqual(self.nodegroups.created, [])
        self.deploy("test_compute_scale_a", compute=compute.name)
        state = self.provisioner.reconcile(compute)
        self.assertEqual(self.nodegroups.created, [compute.nodegroup_name])
        self.assertEqual((state.needed, state.desired, state.ready), (1, 1, 0))
        self.assertTrue(state.provisioning)
        self.deploy("test_compute_scale_b", compute=compute.name)
        self.deploy("test_compute_scale_c", compute=compute.name)
        state = self.provisioner.reconcile(compute)
        self.assertEqual((state.needed, state.desired), (3, 2))
        self.assertIn("maximum of 2", state.message)
        compute.refresh_from_db()
        self.assertEqual((compute.nodegroup_status, compute.desired_nodes), ("ACTIVE", 2))

    def test_reconcile_removes_idle_nodes(self):
        """Test that only ready nodes without LLMHost pods are removed, when they are not needed."""
        compute = self.own_compute("test_compute_idle", gpu={"type": "L4", "count": 1, "memoryGb": 24})
        busy = self.deploy("test_compute_idle_busy", compute=compute.name)
        idle = self.deploy("test_compute_idle_gone", compute=compute.name)
        self.provisioner.reconcile(compute)
        self.join_nodes(compute)
        names = sorted(
            n["metadata"]["name"] for n in self.cluster.list_resources("nodes", f"smarter.sh/compute={compute.name}")
        )
        self.cluster.add_pod("busy-pod", {"smarter.sh/compute": compute.name}, {"phase": "Running"}, node_name=names[0])
        idle.status = "inactive"
        idle.save(update_fields=["status"])
        state = self.provisioner.reconcile(compute)
        self.assertEqual(state.actions, [f"removed idle node {names[1]}"])
        self.assertEqual(self.nodegroups.removed, [f"aws:///us-east-1a/i-{names[1]}"])
        self.assertEqual(state.desired, 1)
        self.assertEqual(busy.compute.pk, compute.pk)

    def test_reconcile_failed_nodegroup(self):
        compute = self.own_compute("test_compute_failed", gpu={"type": "L4", "count": 1, "memoryGb": 24})
        self.deploy("test_compute_failed_a", compute=compute.name)
        self.provisioner.reconcile(compute)
        self.nodegroups.nodegroups[compute.nodegroup_name].status = "CREATE_FAILED"
        self.nodegroups.nodegroups[compute.nodegroup_name].issues = ["InsufficientInstanceCapacity: no g6"]
        state = self.provisioner.reconcile(compute)
        self.assertIn("InsufficientInstanceCapacity", state.message)
        self.assertEqual(state.actions, [])

    def test_unavailable(self):
        compute = self.own_compute("test_compute_unavailable")
        self.nodegroups.ready = False
        self.addCleanup(setattr, self.nodegroups, "ready", True)
        with self.assertRaises(LLMHostComputeError):
            self.provisioner.reconcile(compute)

    def test_delete_nodegroup(self):
        """Test that a node group is not deleted while LLMHosts are deployed on it."""
        compute = self.own_compute("test_compute_delete", gpu={"type": "L4", "count": 1, "memoryGb": 24})
        llmhost = self.deploy("test_compute_delete_a", compute=compute.name)
        with self.assertRaises(LLMHostComputeError):
            self.provisioner.delete_nodegroup(compute)
        llmhost.status = "inactive"
        llmhost.save(update_fields=["status"])
        self.provisioner.delete_nodegroup(compute)
        self.assertEqual(self.nodegroups.deleted, [compute.nodegroup_name])
