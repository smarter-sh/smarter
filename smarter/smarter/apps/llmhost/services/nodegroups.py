"""
Node groups: the cloud's groups of identical nodes, one per.

:class:`~smarter.apps.llmhost.models.LLMHostCompute`.

The service layer manages node groups only through :class:`NodeGroupBackend`, so that it can be
tested with :class:`InMemoryNodeGroupBackend`, and so that another cloud is a new backend.

:class:`EKSNodeGroupBackend`, the default, manages EKS managed node groups of the platform's
cluster, ``smarter_settings.aws_eks_cluster_name``:

- It creates a node group with the EKS API, starting at 0 nodes, and scales it up by raising
  its desired size.
- It removes a node by terminating that node's instance in the node group's Auto Scaling group,
  and lowering its desired size, as the Kubernetes Cluster Autoscaler does. Lowering the desired
  size alone would let the Auto Scaling group choose which instance to terminate, which could
  be a busy one.
- A node group's IAM role and subnets are ``smarter_settings.llmhost_node_role_arn`` and
  ``smarter_settings.llmhost_node_subnet_ids`` if they are set, else those of the cluster's
  first managed node group that Smarter did not create, i.e. the one that Smarter runs on.

Smarter's IAM identity requires: ``eks:CreateNodegroup``, ``eks:DescribeNodegroup``,
``eks:ListNodegroups``, ``eks:UpdateNodegroupConfig``, ``eks:DeleteNodegroup``,
``eks:TagResource``, ``autoscaling:TerminateInstanceInAutoScalingGroup``, and
``iam:PassRole`` on the node role.
"""

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from smarter.apps.llmhost.const import LABEL_COMPUTE
from smarter.apps.llmhost.models.compute import (
    LLMHostCompute,
    LLMHostComputeNodeGroupStatus,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest import running_unit_tests

from .exceptions import LLMHostComputeError

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])
logger_prefix = logging.formatted_text(__name__)

NodeGroupStatus = LLMHostComputeNodeGroupStatus
TAINT_EFFECTS = {"NoSchedule": "NO_SCHEDULE", "NoExecute": "NO_EXECUTE", "PreferNoSchedule": "PREFER_NO_SCHEDULE"}


@dataclass
class NodeGroup:
    """A node group, as the cloud reports it."""

    name: str
    status: str
    desired: int
    max_nodes: int
    issues: list[str] = field(default_factory=list)


class NodeGroupBackend(ABC):
    """The operations that the service layer needs on the cloud's node groups."""

    @property
    @abstractmethod
    def ready(self) -> bool:
        """Whether the cloud is reachable."""

    @abstractmethod
    def describe(self, compute: LLMHostCompute) -> Optional[NodeGroup]:
        """Return the compute's node group, or None if it does not exist."""

    @abstractmethod
    def create(self, compute: LLMHostCompute, desired: int) -> NodeGroup:
        """Create the compute's node group, with ``desired`` nodes."""

    @abstractmethod
    def scale(self, compute: LLMHostCompute, desired: int) -> None:
        """Set the node group's desired size, and its maximum size to the compute's max_nodes."""

    @abstractmethod
    def remove_node(self, compute: LLMHostCompute, provider_id: str) -> None:
        """Terminate one node, by its Kubernetes providerID, and lower the desired size by one."""

    @abstractmethod
    def delete(self, compute: LLMHostCompute) -> None:
        """Delete the compute's node group, and its nodes.

        Idempotent.
        """


def instance_id(provider_id: str) -> str:
    """The EC2 instance id of a node's providerID, e.g. aws:///us-east-1a/i-0abc -> i-0abc."""
    instance = provider_id.rstrip("/").rsplit("/", 1)[-1]
    if not instance.startswith("i-"):
        raise LLMHostComputeError(f"{provider_id} is not the providerID of an EC2 instance.")
    return instance


class EKSNodeGroupBackend(NodeGroupBackend):
    """EKS managed node groups of the platform's cluster."""

    def __init__(self, cluster_name: Optional[str] = None, eks_client=None, autoscaling_client=None):
        self.cluster_name = cluster_name or smarter_settings.aws_eks_cluster_name
        self._eks = eks_client
        self._autoscaling = autoscaling_client
        self._defaults: Optional[tuple[str, list[str]]] = None

    def _session(self):
        # pylint: disable=import-outside-toplevel
        from smarter.apps.infrastructure.providers.aws import AWSProvider
        from smarter.apps.infrastructure.services import infrastructure

        if running_unit_tests():
            # a safety net: the platform's AWS credentials are real, and node groups cost money.
            raise LLMHostComputeError(
                "EKSNodeGroupBackend is disabled in tests. Install an InMemoryNodeGroupBackend with configure_nodegroups()."
            )

        provider = infrastructure.provider
        if not isinstance(provider, AWSProvider):
            raise LLMHostComputeError(f"EKS node groups require the AWS cloud provider, not {provider.name}.")
        if not provider.ready or provider.session is None:
            raise LLMHostComputeError("AWS is not configured, so node groups cannot be managed.")
        return provider.session

    @property
    def eks(self):
        if self._eks is None:
            self._eks = self._session().client("eks")
        return self._eks

    @property
    def autoscaling(self):
        if self._autoscaling is None:
            self._autoscaling = self._session().client("autoscaling")
        return self._autoscaling

    @property
    def ready(self) -> bool:
        try:
            return bool(self.cluster_name) and self.eks is not None
        except LLMHostComputeError:
            return False

    def _call(self, operation: str, method: Callable[..., Any], **kwargs) -> Any:
        try:
            return method(**kwargs)
        except Exception as e:  # pylint: disable=broad-except
            if type(e).__name__ == "ResourceNotFoundException":
                raise
            raise LLMHostComputeError(f"{operation} failed: {e}") from e

    def describe(self, compute: LLMHostCompute) -> Optional[NodeGroup]:
        try:
            response = self._call(
                "eks:DescribeNodegroup",
                self.eks.describe_nodegroup,
                clusterName=self.cluster_name,
                nodegroupName=compute.nodegroup_name,
            )
        except Exception as e:  # pylint: disable=broad-except
            if type(e).__name__ == "ResourceNotFoundException":
                return None
            raise
        nodegroup = response["nodegroup"]
        scaling = nodegroup.get("scalingConfig", {})
        issues = [
            f"{issue.get('code')}: {issue.get('message')}" for issue in nodegroup.get("health", {}).get("issues", [])
        ]
        return NodeGroup(
            name=nodegroup["nodegroupName"],
            status=nodegroup["status"],
            desired=int(scaling.get("desiredSize", 0)),
            max_nodes=int(scaling.get("maxSize", 0)),
            issues=issues,
        )

    def defaults(self) -> tuple[str, list[str]]:
        """The node role and subnets of new node groups: from settings, else the platform's node group."""
        if self._defaults is not None:
            return self._defaults
        role = smarter_settings.llmhost_node_role_arn
        subnets = list(smarter_settings.llmhost_node_subnet_ids or [])
        if not role or not subnets:
            names = self._call("eks:ListNodegroups", self.eks.list_nodegroups, clusterName=self.cluster_name)
            platform = [name for name in names.get("nodegroups", []) if not name.startswith("smarter-")]
            if not platform:
                raise LLMHostComputeError(
                    f"EKS cluster {self.cluster_name} has no node group to copy the node role and subnets from. "
                    "Set SMARTER_LLMHOST_NODE_ROLE_ARN and SMARTER_LLMHOST_NODE_SUBNET_IDS."
                )
            nodegroup = self._call(
                "eks:DescribeNodegroup",
                self.eks.describe_nodegroup,
                clusterName=self.cluster_name,
                nodegroupName=platform[0],
            )["nodegroup"]
            role = role or nodegroup["nodeRole"]
            subnets = subnets or list(nodegroup["subnets"])
        self._defaults = (role, subnets)
        return self._defaults

    def create(self, compute: LLMHostCompute, desired: int) -> NodeGroup:
        role, subnets = self.defaults()
        taint = compute.taint
        self._call(
            "eks:CreateNodegroup",
            self.eks.create_nodegroup,
            clusterName=self.cluster_name,
            nodegroupName=compute.nodegroup_name,
            scalingConfig={"minSize": 0, "maxSize": compute.max_nodes, "desiredSize": desired},
            diskSize=compute.disk_size_gb,
            subnets=list(compute.subnet_ids or subnets),
            instanceTypes=[compute.instance_type],
            amiType=compute.ami_type,
            nodeRole=role,
            capacityType=compute.capacity_type,
            labels={LABEL_COMPUTE: compute.name},
            taints=[{"key": taint["key"], "value": taint["value"], "effect": TAINT_EFFECTS[taint["effect"]]}],
            tags={
                "smarter.sh/compute": compute.name,
                "smarter.sh/environment": str(smarter_settings.environment),
                "smarter.sh/managed-by": smarter_settings.platform_name,
            },
        )
        logger.info("%s created node group %s with %s nodes", logger_prefix, compute.nodegroup_name, desired)
        return NodeGroup(compute.nodegroup_name, NodeGroupStatus.CREATING, desired, compute.max_nodes)

    def scale(self, compute: LLMHostCompute, desired: int) -> None:
        self._call(
            "eks:UpdateNodegroupConfig",
            self.eks.update_nodegroup_config,
            clusterName=self.cluster_name,
            nodegroupName=compute.nodegroup_name,
            scalingConfig={"minSize": 0, "maxSize": compute.max_nodes, "desiredSize": desired},
        )
        logger.info("%s scaled node group %s to %s nodes", logger_prefix, compute.nodegroup_name, desired)

    def remove_node(self, compute: LLMHostCompute, provider_id: str) -> None:
        instance = instance_id(provider_id)
        self._call(
            "autoscaling:TerminateInstanceInAutoScalingGroup",
            self.autoscaling.terminate_instance_in_auto_scaling_group,
            InstanceId=instance,
            ShouldDecrementDesiredCapacity=True,
        )
        logger.info("%s removed node %s from node group %s", logger_prefix, instance, compute.nodegroup_name)

    def delete(self, compute: LLMHostCompute) -> None:
        try:
            self._call(
                "eks:DeleteNodegroup",
                self.eks.delete_nodegroup,
                clusterName=self.cluster_name,
                nodegroupName=compute.nodegroup_name,
            )
        except Exception as e:  # pylint: disable=broad-except
            if type(e).__name__ != "ResourceNotFoundException":
                raise
        logger.info("%s deleted node group %s", logger_prefix, compute.nodegroup_name)


class InMemoryNodeGroupBackend(NodeGroupBackend):
    """
    Node groups in memory, for tests and local development.

    A node group is created ``ACTIVE``. :meth:`join_nodes` simulates the cloud starting the
    nodes that the desired size asks for, as Kubernetes Node resources in an
    :class:`~smarter.apps.llmhost.services.cluster.InMemoryClusterBackend`.
    """

    def __init__(self, ready: bool = True):
        self._ready = ready
        self.nodegroups: dict[str, NodeGroup] = {}
        self.created: list[str] = []
        self.removed: list[str] = []
        self.deleted: list[str] = []
        self.fail: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self._ready

    @ready.setter
    def ready(self, value: bool) -> None:
        self._ready = value

    def _check(self) -> None:
        if self.fail:
            raise LLMHostComputeError(self.fail)

    def describe(self, compute: LLMHostCompute) -> Optional[NodeGroup]:
        self._check()
        nodegroup = self.nodegroups.get(compute.nodegroup_name)
        return copy.deepcopy(nodegroup)

    def create(self, compute: LLMHostCompute, desired: int) -> NodeGroup:
        self._check()
        nodegroup = NodeGroup(compute.nodegroup_name, NodeGroupStatus.ACTIVE, desired, compute.max_nodes)
        self.nodegroups[nodegroup.name] = nodegroup
        self.created.append(nodegroup.name)
        return copy.deepcopy(nodegroup)

    def scale(self, compute: LLMHostCompute, desired: int) -> None:
        self._check()
        nodegroup = self.nodegroups[compute.nodegroup_name]
        nodegroup.desired = desired
        nodegroup.max_nodes = compute.max_nodes

    def remove_node(self, compute: LLMHostCompute, provider_id: str) -> None:
        self._check()
        self.nodegroups[compute.nodegroup_name].desired -= 1
        self.removed.append(provider_id)

    def delete(self, compute: LLMHostCompute) -> None:
        self._check()
        self.nodegroups.pop(compute.nodegroup_name, None)
        self.deleted.append(compute.nodegroup_name)


_nodegroup_factory: Optional[Callable[[], NodeGroupBackend]] = None


def configure_nodegroups(factory: Optional[Callable[[], NodeGroupBackend]]) -> None:
    """
    Set the factory of the node group backend that :func:`get_nodegroups` returns.

    Pass None to restore the default, :class:`EKSNodeGroupBackend`. Tests use this to install an
    :class:`InMemoryNodeGroupBackend`.
    """
    global _nodegroup_factory  # pylint: disable=global-statement
    _nodegroup_factory = factory


def get_nodegroups() -> NodeGroupBackend:
    """Return the node group backend."""
    if _nodegroup_factory is not None:
        return _nodegroup_factory()
    return EKSNodeGroupBackend()


__all__ = [
    "EKSNodeGroupBackend",
    "InMemoryNodeGroupBackend",
    "NodeGroup",
    "NodeGroupBackend",
    "configure_nodegroups",
    "get_nodegroups",
    "instance_id",
]
