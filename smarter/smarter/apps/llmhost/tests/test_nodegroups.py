"""
Test the cloud's node groups: :mod:`smarter.apps.llmhost.services.nodegroups`.

The EKS backend is tested with fake boto3 clients: these tests never call AWS.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.llmhost.manifest.brokers.llmhost_compute import (
    compute_spec_to_django_orm,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.spec import (
    SAMLLMHostComputeSpec,
)
from smarter.apps.llmhost.models import LLMHostCompute
from smarter.apps.llmhost.services.exceptions import LLMHostComputeError
from smarter.apps.llmhost.services.nodegroups import (
    EKSNodeGroupBackend,
    InMemoryNodeGroupBackend,
    instance_id,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class ResourceNotFoundException(Exception):
    """Named as boto3 names it, which is how the backend recognizes it."""


def compute(gpu: bool = True, **nodegroup) -> LLMHostCompute:
    """An unsaved LLMHostCompute, with a pk for its node group's name."""
    node = {"instanceType": "g6.2xlarge", "cpu": 8, "memoryGb": 32}
    if gpu:
        node["gpu"] = {"type": "L4", "count": 1, "memoryGb": 24}
    spec = SAMLLMHostComputeSpec(node=node, nodeGroup={"maxNodes": 3, **nodegroup})
    return LLMHostCompute(pk=42, name="test_l4", **compute_spec_to_django_orm(spec))


class TestEKSNodeGroupBackend(SmarterTestBase):
    """Test the EKS managed node group backend, with fake EKS and Auto Scaling clients."""

    def setUp(self):
        self.eks = MagicMock()
        self.autoscaling = MagicMock()
        self.backend = EKSNodeGroupBackend(
            cluster_name="test-cluster", eks_client=self.eks, autoscaling_client=self.autoscaling
        )
        self.eks.list_nodegroups.return_value = {"nodegroups": ["smarter-local-1-other", "platform-nodes"]}
        self.eks.describe_nodegroup.return_value = {
            "nodegroup": {
                "nodegroupName": "platform-nodes",
                "status": "ACTIVE",
                "nodeRole": "arn:aws:iam::123:role/nodes",
                "subnets": ["subnet-a", "subnet-b"],
                "scalingConfig": {"desiredSize": 2, "maxSize": 5},
                "health": {"issues": [{"code": "Ec2SubnetInvalid", "message": "no IPs"}]},
            }
        }

    def test_disabled_in_tests(self):
        """Test the safety net: without injected clients, the backend refuses to reach AWS in tests."""
        backend = EKSNodeGroupBackend(cluster_name="test-cluster")
        with self.assertRaises(LLMHostComputeError):
            backend.eks  # pylint: disable=pointless-statement
        self.assertFalse(backend.ready)

    def test_describe(self):
        nodegroup = self.backend.describe(compute())
        self.assertEqual((nodegroup.status, nodegroup.desired, nodegroup.max_nodes), ("ACTIVE", 2, 5))
        self.assertEqual(nodegroup.issues, ["Ec2SubnetInvalid: no IPs"])
        self.eks.describe_nodegroup.side_effect = ResourceNotFoundException("gone")
        self.assertIsNone(self.backend.describe(compute()))
        self.eks.describe_nodegroup.side_effect = RuntimeError("throttled")
        with self.assertRaises(LLMHostComputeError):
            self.backend.describe(compute())

    def test_create_gpu(self):
        """Test a GPU node group: the NVIDIA AMI, the compute's label, the GPU taint, and the platform's role and subnets."""
        with patch("smarter.apps.llmhost.services.nodegroups.smarter_settings") as settings:
            settings.llmhost_node_role_arn = None
            settings.llmhost_node_subnet_ids = []
            settings.environment = "local"
            settings.platform_name = "smarter"
            nodegroup = self.backend.create(compute(), 1)
        self.assertEqual(nodegroup.status, "CREATING")
        kwargs = self.eks.create_nodegroup.call_args.kwargs
        self.assertEqual(kwargs["clusterName"], "test-cluster")
        self.assertEqual(kwargs["nodegroupName"], compute().nodegroup_name)
        self.assertEqual(kwargs["scalingConfig"], {"minSize": 0, "maxSize": 3, "desiredSize": 1})
        self.assertEqual((kwargs["instanceTypes"], kwargs["amiType"]), (["g6.2xlarge"], "AL2023_x86_64_NVIDIA"))
        self.assertEqual(kwargs["labels"], {"smarter.sh/compute": "test_l4"})
        self.assertEqual(kwargs["taints"], [{"key": "nvidia.com/gpu", "value": "true", "effect": "NO_SCHEDULE"}])
        # the node role and subnets of the first node group that Smarter did not create.
        self.assertEqual(kwargs["nodeRole"], "arn:aws:iam::123:role/nodes")
        self.assertEqual(kwargs["subnets"], ["subnet-a", "subnet-b"])
        self.eks.describe_nodegroup.assert_called_with(clusterName="test-cluster", nodegroupName="platform-nodes")

    def test_create_cpu(self):
        """Test a CPU node group: the standard AMI, the compute's own taint, and its own subnets."""
        with patch("smarter.apps.llmhost.services.nodegroups.smarter_settings") as settings:
            settings.llmhost_node_role_arn = "arn:aws:iam::123:role/llmhost-nodes"
            settings.llmhost_node_subnet_ids = ["subnet-x"]
            settings.environment = "local"
            settings.platform_name = "smarter"
            self.backend.create(compute(gpu=False, subnetIds=["subnet-z"]), 0)
        kwargs = self.eks.create_nodegroup.call_args.kwargs
        self.assertEqual(kwargs["amiType"], "AL2023_x86_64_STANDARD")
        self.assertEqual(kwargs["taints"], [{"key": "smarter.sh/compute", "value": "test_l4", "effect": "NO_SCHEDULE"}])
        self.assertEqual((kwargs["nodeRole"], kwargs["subnets"]), ("arn:aws:iam::123:role/llmhost-nodes", ["subnet-z"]))
        # settings, so no node group is described.
        self.eks.list_nodegroups.assert_not_called()

    def test_no_platform_nodegroup(self):
        self.eks.list_nodegroups.return_value = {"nodegroups": ["smarter-local-1-other"]}
        with patch("smarter.apps.llmhost.services.nodegroups.smarter_settings") as settings:
            settings.llmhost_node_role_arn = None
            settings.llmhost_node_subnet_ids = []
            with self.assertRaises(LLMHostComputeError):
                self.backend.create(compute(), 1)

    def test_scale(self):
        self.backend.scale(compute(), 2)
        self.eks.update_nodegroup_config.assert_called_once_with(
            clusterName="test-cluster",
            nodegroupName=compute().nodegroup_name,
            scalingConfig={"minSize": 0, "maxSize": 3, "desiredSize": 2},
        )

    def test_remove_node(self):
        """Test that a node is removed by terminating its instance, which lowers the desired size."""
        self.backend.remove_node(compute(), "aws:///us-east-1a/i-0abc123")
        self.autoscaling.terminate_instance_in_auto_scaling_group.assert_called_once_with(
            InstanceId="i-0abc123", ShouldDecrementDesiredCapacity=True
        )

    def test_instance_id(self):
        self.assertEqual(instance_id("aws:///ca-central-1b/i-0123"), "i-0123")
        with self.assertRaises(LLMHostComputeError):
            instance_id("gce://project/zone/node")

    def test_delete(self):
        """Test that delete is idempotent."""
        self.backend.delete(compute())
        self.eks.delete_nodegroup.assert_called_once()
        self.eks.delete_nodegroup.side_effect = ResourceNotFoundException("gone")
        self.backend.delete(compute())


class TestInMemoryNodeGroupBackend(SmarterTestBase):
    """Test the in-memory backend that the other tests use."""

    def test_lifecycle(self):
        backend = InMemoryNodeGroupBackend()
        self.assertIsNone(backend.describe(compute()))
        self.assertEqual(backend.create(compute(), 1).status, "ACTIVE")
        backend.scale(compute(), 3)
        self.assertEqual(backend.describe(compute()).desired, 3)
        backend.remove_node(compute(), "aws:///us-east-1a/i-1")
        self.assertEqual(backend.describe(compute()).desired, 2)
        backend.delete(compute())
        self.assertIsNone(backend.describe(compute()))
        backend.fail = "down"
        with self.assertRaises(LLMHostComputeError):
            backend.describe(compute())
