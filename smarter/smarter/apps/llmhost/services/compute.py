"""
Compute: the nodes that LLMHosts run on.

Each :class:`~smarter.apps.llmhost.models.LLMHostCompute` is one node group, whose nodes Smarter
adds and removes itself: it does not assume that the cluster has an autoscaler that knows
about GPU instance types.

- :func:`pod_requests` and :func:`fits` compare an LLMHost's pod to a compute's node.
- :func:`choose_compute` chooses the cheapest active compute that an LLMHost's pod fits.
- :func:`nodes_needed` packs the pods of a compute's LLMHosts onto its nodes.
- :func:`cost_per_hour` is one replica's share of its node's price.
- :class:`ComputeProvisioner` reconciles a compute's node group with its LLMHosts: it creates the
  node group, adds nodes when LLMHosts need them, and removes empty nodes that they no longer do.
- :func:`add_builtin_computes` applies the built-in LLMHostCompute manifests, in ``data/compute``.

A node group has as many nodes as its LLMHosts' pods need, which is usually one per pod: an
LLMHost runs on a node of its own unless its compute's node has room for several of its pods.
"""

import glob
import io
import math
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Optional

from django.db.models import QuerySet
from django.utils import timezone

from smarter.apps.account.models import UserProfile
from smarter.apps.llmhost.const import (
    BUILTIN_COMPUTE_PATH,
    DEFAULT_CPU,
    DEFAULT_MEMORY,
    LABEL_COMPUTE,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostStatusEnum
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostSpec
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.models.compute import (
    LLMHostComputeNodeGroupStatus,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .cluster import ClusterBackend, get_cluster
from .exceptions import LLMHostComputeError
from .nodegroups import NodeGroupBackend, get_nodegroups

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])
logger_prefix = logging.formatted_text(f"{__name__}.ComputeProvisioner")

NodeGroupStatus = LLMHostComputeNodeGroupStatus

QUANTITY_SUFFIXES = {
    "": 1,
    "k": 10**3,
    "M": 10**6,
    "G": 10**9,
    "T": 10**12,
    "P": 10**15,
    "E": 10**18,
    "Ki": 2**10,
    "Mi": 2**20,
    "Gi": 2**30,
    "Ti": 2**40,
    "Pi": 2**50,
    "Ei": 2**60,
}


def cpu_millicores(value: Optional[str]) -> int:
    """A Kubernetes CPU quantity, e.g. 4 or 3500m, in millicores."""
    value = str(value or DEFAULT_CPU).strip()
    if value.endswith("m"):
        return math.ceil(float(value[:-1]))
    return math.ceil(float(value) * 1000)


def memory_mib(value: Optional[str]) -> int:
    """A Kubernetes memory quantity, e.g. 24Gi, in MiB."""
    match = re.match(r"^([0-9.]+)([a-zA-Z]*)$", str(value or DEFAULT_MEMORY).strip())
    if not match or match.group(2) not in QUANTITY_SUFFIXES:
        raise LLMHostComputeError(f"'{value}' is not a Kubernetes memory quantity, e.g. 24Gi.")
    return math.ceil(float(match.group(1)) * QUANTITY_SUFFIXES[match.group(2)] / 2**20)


@dataclass(frozen=True)
class PodRequests:
    """What one replica of an LLMHost requests of its node."""

    cpu_millicores: int
    memory_mib: int
    gpus: int = 0
    vram_gb: int = 0


def pod_requests(spec: SAMLLMHostSpec) -> PodRequests:
    """What one replica of an LLMHost requests, as the renderer requests it."""
    resources = spec.resources
    return PodRequests(
        cpu_millicores=cpu_millicores(resources.cpu),
        memory_mib=memory_mib(resources.memory),
        gpus=resources.gpuCount,
        vram_gb=resources.vramRequiredGb or 0,
    )


def fits(pod: PodRequests, compute: LLMHostCompute) -> list[str]:
    """Why a pod, from :func:`pod_requests`, does not fit one of the compute's nodes.

    Empty if it fits.
    """
    reasons = []
    if pod.gpus > compute.gpu_count:
        reasons.append(f"it requests {pod.gpus} GPUs, and the node has {compute.gpu_count}")
    elif pod.gpus and pod.vram_gb > pod.gpus * compute.gpu_memory_gb:
        reasons.append(
            f"it requires {pod.vram_gb} GB of GPU memory, and {pod.gpus} of the node's GPUs have "
            f"{pod.gpus * compute.gpu_memory_gb} GB"
        )
    if pod.cpu_millicores > compute.allocatable_cpu_millicores:
        reasons.append(
            f"it requests {pod.cpu_millicores}m CPU, and the node can allocate about "
            f"{compute.allocatable_cpu_millicores}m"
        )
    if pod.memory_mib > compute.allocatable_memory_mib:
        reasons.append(
            f"it requests {pod.memory_mib}Mi memory, and the node can allocate about "
            f"{compute.allocatable_memory_mib}Mi"
        )
    return reasons


def cost_per_hour(pod: PodRequests, compute: Optional[LLMHostCompute]) -> Optional[Decimal]:
    """
    One replica's share of its node's price: the largest of its shares of the node's GPUs, CPU.

    and memory, since that is what keeps the rest of the node from other pods.
    """
    if compute is None or compute.price_per_hour is None:
        return None
    shares = [
        Decimal(pod.cpu_millicores) / Decimal(compute.allocatable_cpu_millicores),
        Decimal(pod.memory_mib) / Decimal(compute.allocatable_memory_mib),
    ]
    if compute.gpu_count:
        shares.append(Decimal(pod.gpus) / Decimal(compute.gpu_count))
    return (min(max(shares), Decimal(1)) * compute.price_per_hour).quantize(Decimal("0.0001"))


def choose_compute(pod: PodRequests, computes: Iterable[LLMHostCompute]) -> LLMHostCompute:
    """
    The compute with the cheapest node that a pod, from :func:`pod_requests`, fits.

    By the node's price, not the pod's share of it: an LLMHost usually has a node to itself, so a
    larger node costs more even though a small pod's share of it is less. A pod that requests no
    GPUs is placed on a CPU node, if one fits it.

    :raises LLMHostComputeError: if it fits none.
    """
    candidates = [compute for compute in computes if not fits(pod, compute)]
    if not pod.gpus and any(not compute.has_gpu for compute in candidates):
        candidates = [compute for compute in candidates if not compute.has_gpu]
    if not candidates:
        raise LLMHostComputeError(
            "No LLMHostCompute fits the LLMHost's resources. Reduce spec.resources, or apply an "
            "LLMHostCompute manifest whose node is large enough."
        )

    def price(compute: LLMHostCompute):
        return (compute.price_per_hour is None, compute.price_per_hour or Decimal(0), compute.name)

    return min(candidates, key=price)


def computes_for(user_profile: UserProfile) -> QuerySet:
    """The LLMHostComputes that a user's LLMHosts may run on: those that the user may read."""
    return LLMHostCompute.objects.with_read_permission_for(user_profile.user)  # type: ignore[attr-defined]


def builtin_computes() -> QuerySet:
    """The built-in LLMHostComputes: those that the Smarter admin owns, which every account may use."""
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.utils import smarter_cached_objects

    return LLMHostCompute.objects.filter(user_profile=smarter_cached_objects.smarter_admin_user_profile)


def resolve_compute(spec: SAMLLMHostSpec, user_profile: UserProfile) -> LLMHostCompute:
    """
    The compute of an LLMHost's spec: ``spec.compute``, else :func:`choose_compute`, of those.

    that the LLMHost's owner may read. If several have the name, the owner's own is preferred,
    then their account's, then the Smarter admin's, i.e. the built-in one.

    :raises LLMHostComputeError: if spec.compute does not exist, or the LLMHost's pod does not fit it.
    """
    pod = pod_requests(spec)
    computes = computes_for(user_profile)
    if not spec.compute:
        return choose_compute(pod, computes)
    matches = list(computes.filter(name=spec.compute).select_related("user_profile"))
    if not matches:
        names = sorted(set(computes.values_list("name", flat=True)))
        raise LLMHostComputeError(f"compute: {spec.compute} does not exist. Choose one of: {names}.")

    def precedence(compute: LLMHostCompute) -> int:
        if compute.user_profile_id == user_profile.pk:  # type: ignore[attr-defined]
            return 0
        return 1 if compute.user_profile.account_id == user_profile.account_id else 2  # type: ignore[attr-defined]

    compute = min(matches, key=precedence)
    reasons = fits(pod, compute)
    if reasons:
        raise LLMHostComputeError(f"compute: the LLMHost does not fit a {compute.name} node: {'; '.join(reasons)}.")
    return compute


def nodes_needed(pods: Iterable[PodRequests], compute: LLMHostCompute) -> int:
    """
    The nodes of the compute that the pods need: first fit, largest pod first.

    It packs by the node's estimated allocatable capacity, as the scheduler would place them.
    """
    nodes: list[list[int]] = []
    capacity = [compute.gpu_count, compute.allocatable_cpu_millicores, compute.allocatable_memory_mib]
    for pod in sorted(pods, key=lambda p: (p.gpus, p.memory_mib, p.cpu_millicores), reverse=True):
        need = [pod.gpus, pod.cpu_millicores, pod.memory_mib]
        for free in nodes:
            if all(n <= f for n, f in zip(need, free)):
                for i, n in enumerate(need):
                    free[i] -= n
                break
        else:
            nodes.append([c - n for c, n in zip(capacity, need)])
    return len(nodes)


def node_ready(node: dict[str, Any]) -> bool:
    for condition in node.get("status", {}).get("conditions", []) or []:
        if condition.get("type") == "Ready":
            return condition.get("status") == "True"
    return False


@dataclass
class ComputeState:
    """A compute's node group, compared with what its LLMHosts need."""

    compute: str
    nodegroup_status: str
    needed: int
    desired: int
    ready: int
    nodes: int
    message: str
    actions: list[str] = field(default_factory=list)

    @property
    def provisioning(self) -> bool:
        """Whether nodes are on their way: the node group is being created, or has nodes that are not ready."""
        if self.nodegroup_status in (NodeGroupStatus.CREATING, NodeGroupStatus.UPDATING):
            return True
        return self.ready < min(self.desired, self.needed)

    @property
    def settled(self) -> bool:
        """Whether the node group has the nodes that its LLMHosts need, and no more."""
        return (
            self.nodegroup_status in (NodeGroupStatus.ACTIVE, NodeGroupStatus.ABSENT)
            and self.desired == self.ready == self.nodes
            and self.desired >= self.needed
            and not self.actions
        )


class ComputeProvisioner:
    """
    Reconciles a compute's node group with the LLMHosts that run on it.

    :param cluster: The Kubernetes cluster, whose Nodes and pods it reads.
    :param nodegroups: The cloud's node groups.
    """

    def __init__(self, cluster: Optional[ClusterBackend] = None, nodegroups: Optional[NodeGroupBackend] = None):
        self._cluster = cluster
        self._nodegroups = nodegroups

    @property
    def cluster(self) -> ClusterBackend:
        if self._cluster is None:
            self._cluster = get_cluster()
        return self._cluster

    @property
    def nodegroups(self) -> NodeGroupBackend:
        if self._nodegroups is None:
            self._nodegroups = get_nodegroups()
        return self._nodegroups

    @staticmethod
    def demand(compute: LLMHostCompute) -> list[PodRequests]:
        """
        The pods of the compute's deployed LLMHosts: one per replica.

        From the database, not the cluster, so that an LLMHost being launched counts before its
        pods exist.
        """
        pods: list[PodRequests] = []
        llmhosts = LLMHost.objects.filter(compute=compute, status__in=SAMLLMHostStatusEnum.deployed())
        for llmhost in llmhosts:
            try:
                spec = SAMLLMHostSpec(**(llmhost.spec or {}))
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("%s.demand() skipped %s, whose spec is invalid: %s", logger_prefix, llmhost, e)
                continue
            pods.extend([pod_requests(spec)] * spec.scaling.replicas)
        return pods

    def nodes(self, compute: LLMHostCompute) -> list[dict[str, Any]]:
        """The compute's Kubernetes Nodes."""
        return self.cluster.list_resources("nodes", f"{LABEL_COMPUTE}={compute.name}")

    def busy_nodes(self, compute: LLMHostCompute) -> set[str]:
        """The names of the compute's nodes on which LLMHost pods are scheduled."""
        pods = self.cluster.list_resources("pods", f"{LABEL_COMPUTE}={compute.name}")
        return {pod.get("spec", {}).get("nodeName") for pod in pods if pod.get("spec", {}).get("nodeName")}

    def reconcile(self, compute: LLMHostCompute) -> ComputeState:
        """
        Give the compute's node group the nodes that its LLMHosts need.

        - It creates the node group, if LLMHosts need nodes and it does not exist.
        - It raises the desired size, up to the compute's max_nodes, if they need more nodes.
        - It removes nodes on which no LLMHost pod is scheduled, if they need fewer. Nodes that
          have not joined the cluster yet are not removed: a later reconcile removes them, if
          they are still not needed.

        It is idempotent, and does not wait: a node takes minutes to start, so the
        ``reconcile_llmhost_compute`` task reconciles again until the node group is settled.

        :raises LLMHostComputeError: if the cloud is unavailable, or rejects a change.
        """
        if not self.nodegroups.ready:
            raise LLMHostComputeError("The cloud's node groups cannot be managed: AWS is not configured.")
        needed = nodes_needed(self.demand(compute), compute)
        nodegroup = self.nodegroups.describe(compute)
        nodes = self.nodes(compute)
        ready_nodes = [node for node in nodes if node_ready(node)]
        actions: list[str] = []
        status = nodegroup.status if nodegroup else NodeGroupStatus.ABSENT
        desired = nodegroup.desired if nodegroup else 0
        target = min(needed, compute.max_nodes)
        message = ""

        if nodegroup is None:
            if target:
                nodegroup = self.nodegroups.create(compute, target)
                status, desired = nodegroup.status, nodegroup.desired
                actions.append(f"created node group {compute.nodegroup_name} with {target} nodes")
        elif status in NodeGroupStatus.failed():
            message = (
                f"Node group {nodegroup.name} is {status}: {'; '.join(nodegroup.issues) or 'see the AWS console'}."
            )
        elif status != NodeGroupStatus.ACTIVE:
            message = f"Node group {nodegroup.name} is {status}."
        elif target > desired:
            self.nodegroups.scale(compute, target)
            actions.append(f"scaled node group {nodegroup.name} from {desired} to {target} nodes")
            desired = target
        elif target < desired:
            busy = self.busy_nodes(compute)
            idle = [node for node in ready_nodes if node["metadata"]["name"] not in busy]
            for node in idle[: desired - target]:
                provider_id = node.get("spec", {}).get("providerID", "")
                self.nodegroups.remove_node(compute, provider_id)
                actions.append(f"removed idle node {node['metadata']['name']}")
                desired -= 1

        if not message:
            if needed > compute.max_nodes:
                message = (
                    f"Its LLMHosts need {needed} nodes, more than its maximum of {compute.max_nodes}. "
                    "Raise max_nodes, or destroy an LLMHost."
                )
            elif len(ready_nodes) < min(desired, target):
                message = f"Waiting for {min(desired, target) - len(ready_nodes)} {compute.instance_type} nodes to join the cluster."
            else:
                message = f"{len(ready_nodes)} of {desired} nodes ready, for {needed} needed."
        state = ComputeState(
            compute=compute.name,
            nodegroup_status=status,
            needed=needed,
            desired=desired,
            ready=len(ready_nodes),
            nodes=len(nodes),
            message=message,
            actions=actions,
        )
        self._persist(compute, state)
        for action in actions:
            logger.info("%s.reconcile() %s: %s", logger_prefix, compute, action)
        return state

    @staticmethod
    def _persist(compute: LLMHostCompute, state: ComputeState) -> None:
        compute.nodegroup_status = state.nodegroup_status
        compute.desired_nodes = state.desired
        compute.ready_nodes = state.ready
        compute.status_message = state.message
        compute.last_reconciled_at = timezone.now()
        compute.save(
            update_fields=[
                "nodegroup_status",
                "desired_nodes",
                "ready_nodes",
                "status_message",
                "last_reconciled_at",
                "updated_at",
            ]
        )

    def delete_nodegroup(self, compute: LLMHostCompute) -> None:
        """
        Delete the compute's node group.

        :raises LLMHostComputeError: if LLMHosts still run on it.
        """
        if compute.llmhosts.filter(status__in=SAMLLMHostStatusEnum.deployed()).exists():  # type: ignore[attr-defined]
            raise LLMHostComputeError(f"LLMHosts are deployed on {compute.name}. Destroy them first.")
        self.nodegroups.delete(compute)


def add_builtin_computes(user_profile: Optional[UserProfile] = None, path: str = BUILTIN_COMPUTE_PATH) -> bool:
    """
    Apply the built-in LLMHostCompute manifests, in ``data/compute``, for a user.

    ``manage.py initialize_platform`` applies them for the Smarter admin user, so that every
    account's LLMHosts may choose them. It does not create their node groups: an LLMHost's launch
    does. A manifest that fails to apply is logged and skipped.

    :param user_profile: The owner. Defaults to the Smarter admin.
    :returns: True if every manifest was applied.
    """
    # pylint: disable=import-outside-toplevel
    from django.core.management import call_command

    from smarter.apps.account.utils import smarter_cached_objects

    user_profile = user_profile or smarter_cached_objects.smarter_admin_user_profile
    retval = True
    for filename in sorted(glob.glob(os.path.join(path, "*.yaml"))):
        output, error_output = io.StringIO(), io.StringIO()
        try:
            call_command(
                "apply_manifest",
                filespec=filename,
                username=user_profile.user.username,
                stdout=output,
                stderr=error_output,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error("%s failed to apply LLMHostCompute manifest %s: %s", logger_prefix, filename, e)
            retval = False
    return retval


__all__ = [
    "ComputeProvisioner",
    "ComputeState",
    "add_builtin_computes",
    "PodRequests",
    "choose_compute",
    "cost_per_hour",
    "cpu_millicores",
    "fits",
    "memory_mib",
    "nodes_needed",
    "builtin_computes",
    "computes_for",
    "pod_requests",
    "resolve_compute",
]
