"""
The health of the platform's Kubernetes cluster, as its cloud provider reports it.

Kubernetes itself reports the health of pods and nodes. The cloud provider that runs the cluster reports
what Kubernetes cannot see: whether the control plane is healthy, whether each node group can launch its
instances, whether each add-on (e.g. ``coredns`` or ``vpc-cni``) is healthy and has a newer version, and
the provider's recommendations, e.g. EKS's insights about the cluster's readiness for the next
Kubernetes version.

:meth:`~smarter.apps.infrastructure.providers.base.CloudProvider.get_kubernetes_cluster_health` returns a
:class:`ClusterHealth`, built from these models, whichever cloud runs the cluster. For AWS, the EKS
helper, :meth:`~smarter.apps.infrastructure.providers.aws.helpers.eks.AWSEks.get_cluster_health`, fills it.
Each part is read on its own: a part that cannot be read, e.g. because the platform's cloud credentials
may not list insights, is named in :attr:`ClusterHealth.errors`, and the other parts are still returned.

The MCPServer's staff-only ``eks_status`` tool
(:class:`~smarter.apps.mcpserver.protocol.tools.status.EksStatusTool`) reports it.
"""

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict


class HealthIssue(BaseModel):
    """
    A health issue that the cloud provider reports for the cluster, a node group or an add-on.

    e.g. EKS reports ``Ec2LaunchTemplateNotFound`` for a node group whose launch template was deleted,
    or ``InsufficientNumberOfReplicas`` for an add-on whose pods are not running.
    """

    model_config = ConfigDict(frozen=True)

    code: str
    """The provider's code for the issue, e.g. ``AsgInstanceLaunchFailures``."""

    message: str = ""
    """The provider's explanation of the issue."""

    resources: tuple[str, ...] = ()
    """The provider's ids of the resources that the issue affects, e.g. EC2 instance ids."""


class NodeGroupHealth(BaseModel):
    """
    One node group of the cluster: a set of identical nodes that the cloud provider launches and replaces.

    Its size is kept between its minimum and maximum by the cluster autoscaler, and its status says
    whether the provider can manage it, e.g. ``DEGRADED`` when it cannot launch instances.
    """

    name: str
    """The node group's name."""

    status: str = ""
    """The provider's status, e.g. ``ACTIVE``, ``UPDATING`` or ``DEGRADED``."""

    desired_size: Optional[int] = None
    """The number of nodes that the group runs now, as the autoscaler set it."""

    min_size: Optional[int] = None
    """The fewest nodes that the group may run."""

    max_size: Optional[int] = None
    """The most nodes that the group may run.

    A group at its maximum cannot add room for more pods.
    """

    instance_types: tuple[str, ...] = ()
    """The instance types that the group may launch, e.g. ``("t3.xlarge",)``."""

    capacity_type: str = ""
    """How the instances are bought: ``ON_DEMAND``, or ``SPOT``, which AWS can take back at short notice."""

    release_version: str = ""
    """The version of the nodes' image, e.g. an EKS optimized AMI release."""

    issues: tuple[HealthIssue, ...] = ()
    """The node group's health issues, or none."""


class AddonHealth(BaseModel):
    """
    One add-on of the cluster: a component that the cloud provider installs and updates, e.g. ``coredns``.

    It records the add-on's version, and the newest version that the provider offers for the cluster's
    Kubernetes version, so that an outdated add-on can be reported.
    """

    name: str
    """The add-on's name, e.g. ``coredns``, ``kube-proxy`` or ``vpc-cni``."""

    version: str = ""
    """The add-on's installed version, e.g. ``v1.11.4-eksbuild.2``."""

    status: str = ""
    """The provider's status, e.g. ``ACTIVE``, ``DEGRADED`` or ``UPDATING``."""

    latest_version: Optional[str] = None
    """The newest version for the cluster's Kubernetes version, or None if it could not be read."""

    issues: tuple[HealthIssue, ...] = ()
    """The add-on's health issues, or none."""

    @property
    def update_available(self) -> bool:
        """
        Whether a newer version of the add-on is available for the cluster's Kubernetes version.

        :returns: True if :attr:`latest_version` is known and newer than :attr:`version`, compared by
            their numbers (see :func:`version_key`).
        """
        if not self.latest_version:
            return False
        latest = version_key(self.latest_version)
        installed = version_key(self.version)
        return latest > installed


class ClusterInsight(BaseModel):
    """
    One recommendation of the cloud provider about the cluster, e.g. an EKS insight.

    EKS checks the cluster regularly, e.g. for apis that the next Kubernetes version removes, and reports
    each check as passing, or as a warning or error, with a reason.
    """

    name: str
    """The insight's name, e.g. "Deprecated APIs removed in Kubernetes v1.34"."""

    category: str = ""
    """The kind of insight, e.g. ``UPGRADE_READINESS`` or ``MISCONFIGURATION``."""

    status: str = ""
    """The result of the check: ``PASSING``, ``WARNING``, ``ERROR`` or ``UNKNOWN``."""

    reason: str = ""
    """Why the check has this result, in the provider's words."""

    kubernetes_version: str = ""
    """The Kubernetes version that the insight is about, e.g. the next one, or empty if it is about none."""


class ClusterHealth(BaseModel):
    """
    The health of the platform's Kubernetes cluster: its control plane, node groups, add-ons and insights.

    Every list is empty when its part has nothing in it, or could not be read. :attr:`errors` tells the
    two apart.
    """

    name: str = ""
    """The cluster's name."""

    status: str = ""
    """The control plane's status, e.g. ``ACTIVE``, ``UPDATING`` or ``FAILED``."""

    version: str = ""
    """The cluster's Kubernetes version, e.g. ``1.33``."""

    platform_version: str = ""
    """The provider's version of the control plane, e.g. ``eks.9``."""

    issues: tuple[HealthIssue, ...] = ()
    """The control plane's health issues, or none."""

    nodegroups: list[NodeGroupHealth] = []
    """The cluster's node groups."""

    addons: list[AddonHealth] = []
    """The cluster's add-ons."""

    insights: list[ClusterInsight] = []
    """The provider's insights about the cluster."""

    errors: list[str] = []
    """The parts that could not be read, and why, e.g. ``insights: AccessDeniedException``."""


VERSION_NUMBERS = re.compile(r"\d+")
"""The numbers of a version string, wherever they are, e.g. 1, 19, 0 and 2 in ``v1.19.0-eksbuild.2``."""


def version_key(version: str) -> tuple[int, ...]:
    """
    Turn a version into a tuple of its numbers, so that versions compare as versions, not as text.

    As text, ``v1.9.0`` sorts after ``v1.19.0``. As tuples, ``(1, 9, 0)`` sorts before ``(1, 19, 0)``.

    :param version: The version, e.g. ``v1.19.0-eksbuild.2``.
    :returns: Its numbers, in order, e.g. ``(1, 19, 0, 2)``, or an empty tuple if it has none.
    """
    numbers = VERSION_NUMBERS.findall(version)
    return tuple(int(number) for number in numbers)


__all__ = [
    "AddonHealth",
    "ClusterHealth",
    "ClusterInsight",
    "HealthIssue",
    "NodeGroupHealth",
    "version_key",
]
