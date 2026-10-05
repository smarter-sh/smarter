"""
LLMHostCompute: a kind of node that LLMHosts run on, configured by an LLMHostCompute manifest.

One LLMHostCompute is one node group of the cluster, e.g. on AWS, one EKS managed node group
of one instance type. An LLMHost chooses an LLMHostCompute, and its pods run only on that node
group's nodes. Smarter creates the node group, and adds and removes its nodes as LLMHosts are
launched and destroyed: see :mod:`smarter.apps.llmhost.services.compute`.

Like other Smarter resources, an LLMHostCompute is owned by a user, and its visibility is
determined by ownership and role: the built-in LLMHostComputes are owned by the Smarter admin,
so every account's LLMHosts may choose them.

The manifest's ``spec`` is stored, as it is, in :attr:`LLMHostCompute.spec`. The other fields
are copies of the parts of the spec that sizing and node groups use, and the node group's
observed state.
"""

import re

from django.db import models

from smarter.apps.account.models import MetaDataWithOwnershipModel
from smarter.apps.llmhost.const import TAINT_COMPUTE, TAINT_GPU
from smarter.common.conf import smarter_settings


class LLMHostComputeNodeGroupStatus:
    """The status of an LLMHostCompute's node group, as the cloud reports it, or ``absent``."""

    ABSENT = "absent"
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    CREATE_FAILED = "CREATE_FAILED"
    DELETE_FAILED = "DELETE_FAILED"
    DEGRADED = "DEGRADED"

    @classmethod
    def failed(cls) -> list[str]:
        return [cls.CREATE_FAILED, cls.DELETE_FAILED, cls.DEGRADED]


class LLMHostCompute(MetaDataWithOwnershipModel):
    """
    A kind of node, e.g. g6.2xlarge with one NVIDIA L4, and its node group.

    The node's capacity is what the instance type provides. What pods can request, its
    allocatable capacity, is less: the kubelet, the operating system and the cluster's
    DaemonSets reserve some of it. See :attr:`allocatable_cpu_millicores` and
    :attr:`allocatable_memory_mib`.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "LLMHost Compute"
        verbose_name_plural = "LLMHost Compute"
        unique_together = ("user_profile", "name")

    # --- the manifest's spec, as it is -----------------------------------
    spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="The manifest's spec, in camelCase. The source of truth for the node group.",
    )

    # --- the node --------------------------------------------------------------
    instance_type = models.CharField(max_length=50, help_text="e.g. 'g6.2xlarge'.")
    cpu = models.PositiveIntegerField(default=1, help_text="vCPUs.")
    memory_gb = models.PositiveIntegerField(default=1, help_text="GiB.")
    gpu_type = models.CharField(max_length=50, blank=True, default="", help_text="e.g. 'L4'.")
    gpu_count = models.PositiveSmallIntegerField(default=0)
    gpu_memory_gb = models.PositiveIntegerField(default=0, help_text="Per GPU.")
    max_nodes = models.PositiveSmallIntegerField(default=4, help_text="The most nodes that Smarter adds.")
    price_per_hour = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, help_text="Of one node, e.g. its on-demand price."
    )

    # --- observed state ------------------------------------------------------------
    nodegroup_status = models.CharField(max_length=20, default=LLMHostComputeNodeGroupStatus.ABSENT)
    desired_nodes = models.PositiveSmallIntegerField(default=0)
    ready_nodes = models.PositiveSmallIntegerField(default=0)
    status_message = models.TextField(blank=True, default="")
    last_reconciled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name}"

    def clone(self, new_name=None, new_version=None, user_profile=None) -> "LLMHostCompute":
        """Clone the LLMHostCompute's spec, but not its node group: the clone is a new kind of node, whose node group Smarter creates when an LLMHost first needs one of its nodes."""
        clone = super().clone(new_name=new_name, new_version=new_version, user_profile=user_profile)
        clone.nodegroup_status = LLMHostComputeNodeGroupStatus.ABSENT
        clone.desired_nodes = 0
        clone.ready_nodes = 0
        clone.status_message = ""
        clone.last_reconciled_at = None
        clone.save()
        return clone  # type: ignore[return-value]

    def rename(self, new_name: str) -> "LLMHostCompute":
        """
        Rename the LLMHostCompute.

        Refused while its node group exists, whose name includes the
        LLMHostCompute's, or while LLMHosts use it, whose spec.compute names it.

        :raises ValueError: if it cannot be renamed.
        """
        if self.nodegroup_status != LLMHostComputeNodeGroupStatus.ABSENT:
            raise ValueError(f"{self.name} cannot be renamed while its node group {self.nodegroup_name} exists.")
        if self.pk and self.llmhosts.exists():  # type: ignore[attr-defined]
            raise ValueError(f"{self.name} cannot be renamed while LLMHosts use it.")
        return super().rename(new_name)  # type: ignore[return-value]

    @property
    def has_gpu(self) -> bool:
        return self.gpu_count > 0

    @property
    def node_spec(self) -> dict:
        """Spec.node, as stored."""
        return (self.spec or {}).get("node", {}) or {}

    @property
    def nodegroup_spec(self) -> dict:
        """Spec.nodeGroup, as stored."""
        return (self.spec or {}).get("nodeGroup", {}) or {}

    @property
    def gpu_resource(self) -> str:
        return (self.node_spec.get("gpu") or {}).get("resource") or "nvidia.com/gpu"

    @property
    def disk_size_gb(self) -> int:
        return int(self.node_spec.get("diskSizeGb") or 100)

    @property
    def capacity_type(self) -> str:
        return self.node_spec.get("capacityType") or "ON_DEMAND"

    @property
    def ami_type(self) -> str:
        if self.node_spec.get("amiType"):
            return self.node_spec["amiType"]
        return "AL2023_x86_64_NVIDIA" if self.has_gpu else "AL2023_x86_64_STANDARD"

    @property
    def subnet_ids(self) -> list[str]:
        return list(self.nodegroup_spec.get("subnetIds") or [])

    @property
    def nodegroup_name(self) -> str:
        """The node group's name, unique to the environment, e.g. smarter-alpha-12-gpu-l4-1x."""
        environment = re.sub(r"[^a-z0-9-]+", "-", str(smarter_settings.environment).lower())
        name = re.sub(r"[^a-z0-9-]+", "-", self.name.lower()).strip("-")
        return f"smarter-{environment}-{self.pk}-{name}"[:63].rstrip("-")

    @property
    def taint(self) -> dict[str, str]:
        """The node group's taint, which LLMHost pods tolerate."""
        if self.has_gpu:
            return {"key": TAINT_GPU, "value": "true", "effect": "NoSchedule"}
        return {"key": TAINT_COMPUTE, "value": self.name, "effect": "NoSchedule"}

    @property
    def allocatable_cpu_millicores(self) -> int:
        """
        An estimate of the CPU that pods can request on one node.

        The kubelet's reservation, and the cluster's DaemonSets, e.g. the CNI, kube-proxy and the
        NVIDIA device plugin: half a core plus 2%.
        """
        total = self.cpu * 1000
        return total - 500 - total * 2 // 100

    @property
    def allocatable_memory_mib(self) -> int:
        """An estimate of the memory that pods can request on one node: less 1.5 GiB plus 3%."""
        total = self.memory_gb * 1024
        return total - 1536 - total * 3 // 100


__all__ = ["LLMHostCompute", "LLMHostComputeNodeGroupStatus"]
