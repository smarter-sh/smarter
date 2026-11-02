"""
A snapshot of the platform's Kubernetes workload: its pods, the cluster's nodes, and recent warnings.

The Smarter Operations MCP server's ``platform_status`` tool
(:class:`~smarter.apps.mcpserver.status.tools.PlatformStatusTool`) uses this module to answer help
desk questions such as "is Smarter down?" or "why is it slow?". :func:`cluster_snapshot` reads, at
the moment it is called:

- the **pods** of the environment's namespace, e.g. ``smarter-platform-prod``: whether each one is
  ready, how often it has restarted, and what is wrong with it, e.g. ``CrashLoopBackOff``, or a
  last restart that was ``OOMKilled``.
- the **nodes** of the cluster, which every environment shares: whether each one is ready, and
  whether it reports a pressure condition, such as ``MemoryPressure``.
- the CPU and memory that each pod and node **uses**, from `metrics-server
  <https://github.com/kubernetes-sigs/metrics-server>`__, which every environment installs. These are
  the numbers that ``kubectl top`` shows. They are compared with the pods' memory limits and the
  nodes' allocatable capacity, to spot what is about to run out.
- the **warning events** of the namespace, e.g. ``BackOff`` or ``FailedScheduling``, of the last
  minutes.

Everything is read through :data:`smarter.apps.infrastructure.services.infrastructure`
``.kubernetes``, with
:meth:`~smarter.apps.infrastructure.services.kubernetes.KubernetesService.find_resources`, which tells
a cluster that could not be read from one that has nothing to list. Each read is one ``kubectl get``
call, five in all, and nothing is cached: the snapshot is always current. Nothing is written to the
cluster, and nothing reaches a cloud monitoring service, such as CloudWatch, which would add cost.

A part that cannot be read, e.g. because metrics-server is not installed, is named in
:attr:`ClusterSnapshot.errors`, and the other parts are still returned, so that one failure never
hides the rest of the picture.

Kubernetes writes quantities with suffixes: CPU in cores or millicores, e.g. ``2`` or ``250m``, and
memory in bytes, e.g. ``1280Mi`` or ``2Gi``. :func:`parse_cpu` and :func:`parse_memory` turn them into
plain numbers, so that they can be added and compared.

**Example usage:**

.. code-block:: python

    from smarter.apps.mcpserver.status.cluster import cluster_snapshot
    from smarter.common.conf import smarter_settings

    snapshot = cluster_snapshot(smarter_settings.environment_namespace, minutes=60)
    for pod in snapshot.pods:
        if not pod.ready:
            print(pod.name, pod.problem)

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from smarter.apps.infrastructure.services import infrastructure
from smarter.lib.typing import SmarterDictType

NODE_PRESSURES = ("MemoryPressure", "DiskPressure", "PIDPressure", "NetworkUnavailable")
"""
The node conditions that mean a problem when their status is ``True``.

A node reports each of them, normally as ``False``. ``MemoryPressure`` and ``DiskPressure`` mean
that the kubelet is about to evict pods to free memory or disk, ``PIDPressure`` that the node is
running out of process ids, and ``NetworkUnavailable`` that its network is not configured.
"""

CPU_UNITS = {"n": 1e-9, "u": 1e-6, "m": 1e-3, "": 1.0}
"""
The suffixes of a Kubernetes CPU quantity, and how many cores one unit of each is.

A pod's requests and limits use millicores, e.g. ``250m`` for a quarter of a core. metrics-server
reports use in nanocores, e.g. ``123456789n``. A number without a suffix is whole cores.
"""

MEMORY_UNITS = {
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
    "k": 1000,
    "K": 1000,
    "M": 1000**2,
    "G": 1000**3,
    "T": 1000**4,
    "": 1,
}
"""
The suffixes of a Kubernetes memory quantity, and how many bytes one unit of each is.

``Ki``, ``Mi``, ``Gi`` and ``Ti`` are powers of 1024, which the platform's Helm chart uses, e.g.
``1280Mi``. ``k``, ``M``, ``G`` and ``T`` are powers of 1000. A number without a suffix is bytes.
"""

QUANTITY = re.compile(r"^([0-9.]+)([A-Za-z]*)$")
"""A Kubernetes quantity: a number, then an optional suffix, e.g. ``250m`` or ``1280Mi``."""


def split_quantity(quantity: Optional[str]) -> Optional[tuple[float, str]]:
    """
    Split a Kubernetes quantity into its number and its suffix.

    :param quantity: The quantity, e.g. ``1280Mi``, ``250m`` or ``2``. None and an empty string are
        allowed, for a request or limit that a pod does not set.
    :returns: The number and the suffix, e.g. ``(1280.0, "Mi")``, or ``(2.0, "")`` for a number without
        a suffix. None if the quantity is missing, or is not a number followed by letters.
    """
    text = str(quantity or "").strip()
    match = QUANTITY.match(text)
    if match is None:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    return number, suffix


def parse_cpu(quantity: Optional[str]) -> Optional[float]:
    """
    Convert a Kubernetes CPU quantity into cores.

    :param quantity: The quantity, e.g. a pod's request of ``250m``, a node's allocatable ``3920m``,
        or metrics-server's use of ``123456789n``.
    :returns: The cores, e.g. 0.25 for ``250m``. None if the quantity is missing, or its suffix is not
        one of :data:`CPU_UNITS`, e.g. a memory quantity such as ``1Gi``.
    """
    parts = split_quantity(quantity)
    if parts is None:
        return None
    number, suffix = parts
    if suffix not in CPU_UNITS:
        return None
    return number * CPU_UNITS[suffix]


def parse_memory(quantity: Optional[str]) -> Optional[int]:
    """
    Convert a Kubernetes memory quantity into bytes.

    :param quantity: The quantity, e.g. a pod's limit of ``2Gi``, a node's allocatable ``15000Mi``, or
        metrics-server's use of ``123456Ki``.
    :returns: The bytes, rounded down, e.g. 2147483648 for ``2Gi``. None if the quantity is missing,
        or its suffix is not one of :data:`MEMORY_UNITS`, e.g. a CPU quantity such as ``250m``.
    """
    parts = split_quantity(quantity)
    if parts is None:
        return None
    number, suffix = parts
    if suffix not in MEMORY_UNITS:
        return None
    return int(number * MEMORY_UNITS[suffix])


def mebibytes(value: Optional[int]) -> str:
    """
    Format bytes as mebibytes, the unit that the platform's Helm chart uses for memory.

    :param value: The bytes, e.g. from :func:`parse_memory`, or None if they are unknown.
    :returns: The mebibytes, rounded, with Kubernetes' suffix, e.g. ``512Mi``, or ``?`` if they are
        unknown, e.g. because metrics-server could not be read.
    """
    if value is None:
        return "?"
    mib = value / 1024**2
    return f"{mib:.0f}Mi"


def percent(used: Optional[float], capacity: Optional[float]) -> Optional[int]:
    """
    Express a use as a whole percentage of a capacity, e.g. a pod's memory of its limit.

    :param used: The amount in use, e.g. bytes of memory or cores of CPU.
    :param capacity: The most that may be used, in the same unit, e.g. the pod's memory limit.
    :returns: The percentage, rounded, which may be above 100. None if either amount is unknown, or
        the capacity is zero, e.g. for a pod that sets no memory limit.
    """
    if used is None:
        return None
    if not capacity:
        return None
    return round(100 * used / capacity)


def parse_time(value: Optional[str]) -> Optional[datetime]:
    """
    Convert a Kubernetes timestamp into a time in UTC.

    :param value: The timestamp, in RFC 3339 format, as Kubernetes writes it, e.g.
        ``2026-11-02T14:00:00Z``, or with fractions of a second, as an event's ``eventTime`` has.
    :returns: The time, in UTC. None if the value is missing or is not a timestamp.
    """
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return None
    return when.astimezone(timezone.utc)


def total_cores(values: Iterable[Optional[float]]) -> Optional[float]:
    """
    Add up CPU amounts that may be unknown, e.g. the CPU requests of a pod's containers.

    :param values: The cores of each container. A container that does not set a request is None.
    :returns: The sum of the known amounts, or None if none is known, so that "unknown" is never
        reported as zero.
    """
    known = []
    for value in values:
        if value is not None:
            known.append(value)
    if not known:
        return None
    return sum(known)


def total_bytes(values: Iterable[Optional[int]]) -> Optional[int]:
    """
    Add up memory amounts that may be unknown, e.g. the memory limits of a pod's containers.

    :param values: The bytes of each container. A container that does not set a limit is None.
    :returns: The sum of the known amounts, or None if none is known, so that "unknown" is never
        reported as zero.
    """
    known = []
    for value in values:
        if value is not None:
            known.append(value)
    if not known:
        return None
    return sum(known)


def section(item: SmarterDictType, key: str) -> SmarterDictType:
    """
    Return one section of a Kubernetes resource, e.g. its ``metadata``, ``spec`` or ``status``.

    A resource from ``kubectl get -o json`` may leave out a section, or set it to null, e.g. the
    ``lastState`` of a container that never restarted. This returns an empty dict for both, so that
    the caller can read keys from it without checking first.

    :param item: The resource, or a section of one.
    :param key: The section's name, e.g. ``status``.
    :returns: The section, or an empty dict if the resource has none.
    """
    value = item.get(key)
    if isinstance(value, dict):
        return value
    return {}


@dataclass
class PodStatus:  # pylint: disable=too-many-instance-attributes  (a record: its fields are its purpose)
    """
    The state of one pod of the environment, as ``platform_status`` reports it.

    It is built from the pod's Kubernetes resource by :func:`pod_status`, and its use of CPU and
    memory is added from metrics-server by :func:`read_pods`. A pod is the running copy of one of the
    platform's components, e.g. one of the two ``smarter`` app servers.
    """

    name: str
    """The pod's name, e.g. ``smarter-6f9c7d-a1b2c``.

    It changes on every deploy and restart.
    """

    component: str
    """What the pod runs, e.g. ``smarter``, ``smarter-worker`` or ``mariadb``.

    See :func:`component_of`.
    """

    phase: str = ""
    """Kubernetes' phase of the pod: ``Pending``, ``Running``, ``Succeeded``, ``Failed`` or ``Unknown``."""

    node: str = ""
    """The name of the node that the pod runs on, or empty while it is not scheduled."""

    ready_containers: int = 0
    """How many of the pod's containers are ready to serve."""

    containers: int = 0
    """How many containers the pod has."""

    restarts: int = 0
    """How often the pod's containers have restarted since the pod was created, all added up."""

    problem: str = ""
    """
    What is wrong with the pod, or an empty string if nothing is.

    e.g. ``CrashLoopBackOff``, ``ImagePullBackOff``, ``Pending``, or ``last restart: OOMKilled`` for
    a pod that runs now, but was killed for lack of memory before. See :func:`container_problem`.
    """

    started: Optional[datetime] = None
    """When the pod started, in UTC, or None if it has not started yet."""

    cpu: Optional[float] = None
    """The cores that the pod uses now, from metrics-server, or None if they could not be read."""

    memory: Optional[int] = None
    """The bytes of memory that the pod uses now, from metrics-server, or None if they could not be read."""

    cpu_request: Optional[float] = None
    """The cores that the pod's containers request, which the scheduler reserves for it, or None."""

    memory_request: Optional[int] = None
    """The bytes of memory that the pod's containers request, or None if they request none."""

    memory_limit: Optional[int] = None
    """
    The most bytes of memory that the pod's containers may use, or None if they set no limit.

    A container that uses more is killed, and its last state is ``OOMKilled``.
    """

    @property
    def ready(self) -> bool:
        """
        Whether the pod is ready to serve: it has containers, and every one of them is ready.

        :returns: False for a pod that has no containers yet, e.g. one that is still being scheduled.
        """
        if self.containers == 0:
            return False
        return self.ready_containers == self.containers


@dataclass
class NodeStatus:  # pylint: disable=too-many-instance-attributes  (a record: its fields are its purpose)
    """
    The state of one node of the Kubernetes cluster, as ``platform_status`` reports it.

    A node is one EC2 instance that runs pods. The cluster's nodes are shared by every environment,
    so a node's problem can affect every environment. It is built from the node's Kubernetes resource
    by :func:`node_status`, and its use of CPU and memory is added from metrics-server by
    :func:`read_nodes`.
    """

    name: str
    """The node's name, e.g. ``ip-10-0-0-1.ec2.internal``."""

    ready: bool = False
    """Whether the node's ``Ready`` condition is ``True``: its kubelet is healthy, and it can run pods."""

    unschedulable: bool = False
    """Whether the node is cordoned: it keeps its pods, but no new pod is scheduled on it, e.g. during a drain."""

    pressures: list[str] = field(default_factory=list)
    """The conditions of :data:`NODE_PRESSURES` that the node reports as ``True``, e.g. ``["MemoryPressure"]``."""

    instance_type: str = ""
    """The node's EC2 instance type, e.g. ``t3.xlarge``, from its ``node.kubernetes.io/instance-type`` label."""

    capacity_type: str = ""
    """
    How the node is bought: ``ON_DEMAND`` or ``SPOT``, or an empty string if the node does not say.

    A spot node can be taken back by AWS at two minutes' notice, which restarts its pods.
    """

    created: Optional[datetime] = None
    """When the node joined the cluster, in UTC.

    A young node may have replaced one that was taken away.
    """

    cpu: Optional[float] = None
    """The cores that the node uses now, from metrics-server, or None if they could not be read."""

    memory: Optional[int] = None
    """The bytes of memory that the node uses now, from metrics-server, or None if they could not be read."""

    cpu_allocatable: Optional[float] = None
    """The cores that pods may use on the node, i.e. its capacity less what the system reserves."""

    memory_allocatable: Optional[int] = None
    """The bytes of memory that pods may use on the node, i.e. its capacity less what the system reserves."""


@dataclass
class WarningEvent:
    """
    A Kubernetes event of type ``Warning`` in the environment's namespace, as ``platform_status`` reports it.

    Kubernetes records an event when something happens to a resource, and marks the ones that need
    attention as warnings, e.g. a container that keeps crashing (``BackOff``), or a pod that no node
    has room for (``FailedScheduling``). It is built from the event's resource by :func:`warning_event`.
    """

    last_seen: Optional[datetime]
    """When the event last happened, in UTC, or None if the event does not say."""

    object: str
    """The resource that the event is about, as ``kind/name``, e.g. ``pod/smarter-worker-5b8d4c-x9y8z``."""

    reason: str
    """Kubernetes' short reason, e.g. ``BackOff``, ``FailedScheduling`` or ``Unhealthy``."""

    message: str
    """Kubernetes' explanation, e.g. ``Back-off restarting failed container smarter-worker``."""

    count: int = 1
    """How many times the event happened.

    Kubernetes counts repeats rather than recording each one.
    """


@dataclass
class ClusterSnapshot:
    """
    The environment's pods, the cluster's nodes, and the namespace's recent warning events, at one moment.

    :func:`cluster_snapshot` returns it, and
    :class:`~smarter.apps.mcpserver.status.tools.PlatformStatusTool` reports it. Every list is empty
    until it is read, and stays empty if it could not be read, in which case :attr:`errors` says so.
    """

    namespace: str
    """The environment's Kubernetes namespace, e.g. ``smarter-platform-prod``."""

    pods: list[PodStatus] = field(default_factory=list)
    """The namespace's pods, except finished Job pods, sorted by component, then name."""

    nodes: list[NodeStatus] = field(default_factory=list)
    """The cluster's nodes, sorted by name."""

    events: list[WarningEvent] = field(default_factory=list)
    """The namespace's warning events of the period, newest first."""

    errors: list[str] = field(default_factory=list)
    """
    The parts that could not be read, and why, e.g. ``pod metrics: metrics-server could not be read``.

    A part that is missing here, and has an empty list, was read, and had nothing in it.
    """


def component_of(pod: SmarterDictType) -> str:
    """
    Name the platform component that a pod runs, from its labels.

    The Helm chart labels each of the platform's pods with ``app.kubernetes.io/name``, e.g.
    ``smarter-worker``. A Job's pod, e.g. the nightly database backup's, has a ``job-name`` label
    instead, and some third-party charts use ``app``.

    :param pod: The pod, as ``kubectl get pod -o json`` returns it.
    :returns: The first of the labels ``app.kubernetes.io/name``, ``job-name`` and ``app`` that the
        pod has, or else the pod's own name.
    """
    metadata = section(pod, "metadata")
    labels = section(metadata, "labels")
    for label in ("app.kubernetes.io/name", "job-name", "app"):
        if labels.get(label):
            return str(labels[label])
    return str(metadata.get("name", ""))


def container_problem(container: SmarterDictType) -> str:
    """
    Describe what is wrong with one of a pod's containers, from its status.

    A container's ``state`` is what it is doing now, and its ``lastState`` is how it ended the last
    time it ran. The current state comes first: a container that is waiting, e.g. in
    ``CrashLoopBackOff``, or has stopped, is the problem now. A container that runs, but restarted
    before, reports why it restarted, e.g. ``OOMKilled``, because that is often why a user saw an error.

    :param container: One item of the pod's ``status.containerStatuses``.
    :returns: Why the container is waiting, e.g. ``CrashLoopBackOff``, or why it stopped, or why it
        last restarted, e.g. ``last restart: OOMKilled``, or an empty string if nothing is wrong.
    """
    state = section(container, "state")
    waiting = section(state, "waiting")
    if waiting.get("reason"):
        return str(waiting["reason"])
    terminated = section(state, "terminated")
    if terminated.get("reason"):
        return str(terminated["reason"])
    last_state = section(container, "lastState")
    last_terminated = section(last_state, "terminated")
    if last_terminated.get("reason"):
        return f"last restart: {last_terminated['reason']}"
    return ""


def container_resources(pod: SmarterDictType, kind: str) -> list[SmarterDictType]:
    """
    List the resource requests, or the resource limits, of each of a pod's containers.

    :param pod: The pod, as ``kubectl get pod -o json`` returns it.
    :param kind: ``requests``, what the scheduler reserves for the container, or ``limits``, the most
        that it may use.
    :returns: One dict per container, in order, e.g. ``{"cpu": "250m", "memory": "1280Mi"}``. A
        container that sets none has an empty dict.
    """
    spec = section(pod, "spec")
    result = []
    for container in spec.get("containers", []):
        resources = section(container, "resources")
        result.append(section(resources, kind))
    return result


def pod_status(pod: SmarterDictType) -> PodStatus:
    """
    Build the status of a pod from its Kubernetes resource.

    It counts the ready containers and the restarts of all of the pod's containers, takes the first
    problem that a container reports (see :func:`container_problem`), and adds up the containers'
    CPU and memory requests and memory limits. A pod that is ``Pending`` without a container problem,
    e.g. one that no node has room for, reports its phase, or Kubernetes' reason for it, as its
    problem. The pod's use of CPU and memory is not in its resource: :func:`read_pods` adds it.

    :param pod: The pod, as ``kubectl get pod -o json`` returns it.
    :returns: The pod's status, without its CPU and memory use.
    """
    metadata = section(pod, "metadata")
    spec = section(pod, "spec")
    status = section(pod, "status")
    containers = status.get("containerStatuses") or []

    ready_containers = 0
    restarts = 0
    problem = ""
    for container in containers:
        if container.get("ready"):
            ready_containers += 1
        restarts += int(container.get("restartCount") or 0)
        if not problem:
            problem = container_problem(container)
    if not problem and status.get("phase") == "Pending":
        problem = str(status.get("reason") or "Pending")

    requests = container_resources(pod, "requests")
    limits = container_resources(pod, "limits")
    cpu_requests = [parse_cpu(request.get("cpu")) for request in requests]
    memory_requests = [parse_memory(request.get("memory")) for request in requests]
    memory_limits = [parse_memory(limit.get("memory")) for limit in limits]

    return PodStatus(
        name=str(metadata.get("name", "")),
        component=component_of(pod),
        phase=str(status.get("phase", "")),
        node=str(spec.get("nodeName", "")),
        ready_containers=ready_containers,
        containers=len(containers),
        restarts=restarts,
        problem=problem,
        started=parse_time(status.get("startTime")),
        cpu_request=total_cores(cpu_requests),
        memory_request=total_bytes(memory_requests),
        memory_limit=total_bytes(memory_limits),
    )


def node_status(node: SmarterDictType) -> NodeStatus:
    """
    Build the status of a node from its Kubernetes resource.

    It reads the node's conditions (``Ready`` and those of :data:`NODE_PRESSURES`), whether it is
    cordoned, its instance type, whether it is a spot or an on-demand instance, from the label of an
    EKS managed node group or of Karpenter, and the CPU and memory that pods may use on it. The
    node's use of CPU and memory is not in its resource: :func:`read_nodes` adds it.

    :param node: The node, as ``kubectl get node -o json`` returns it.
    :returns: The node's status, without its CPU and memory use.
    """
    metadata = section(node, "metadata")
    labels = section(metadata, "labels")
    spec = section(node, "spec")
    status = section(node, "status")
    allocatable = section(status, "allocatable")

    conditions = {}
    for condition in status.get("conditions") or []:
        conditions[condition.get("type")] = condition.get("status")
    pressures = []
    for pressure in NODE_PRESSURES:
        if conditions.get(pressure) == "True":
            pressures.append(pressure)

    capacity_type = labels.get("eks.amazonaws.com/capacityType")
    if not capacity_type:
        capacity_type = labels.get("karpenter.sh/capacity-type", "")

    return NodeStatus(
        name=str(metadata.get("name", "")),
        ready=conditions.get("Ready") == "True",
        unschedulable=bool(spec.get("unschedulable")),
        pressures=pressures,
        instance_type=str(labels.get("node.kubernetes.io/instance-type", "")),
        capacity_type=str(capacity_type),
        created=parse_time(metadata.get("creationTimestamp")),
        cpu_allocatable=parse_cpu(allocatable.get("cpu")),
        memory_allocatable=parse_memory(allocatable.get("memory")),
    )


def warning_event(event: SmarterDictType) -> WarningEvent:
    """
    Build a warning event from its Kubernetes resource.

    Kubernetes has two versions of the event api, and records when an event last happened in
    different places: ``series.lastObservedTime`` for a repeated event of the newer api,
    ``lastTimestamp`` in the older one, and ``eventTime`` for a new event of the newer one. The first
    one that is set is used, and the event's creation time if none is.

    :param event: The event, as ``kubectl get event -o json`` returns it. Its ``type`` is not checked:
        :func:`read_events` passes only warnings.
    :returns: The event.
    """
    involved = section(event, "involvedObject")
    series = section(event, "series")
    metadata = section(event, "metadata")

    last_seen = parse_time(series.get("lastObservedTime"))
    if last_seen is None:
        last_seen = parse_time(event.get("lastTimestamp"))
    if last_seen is None:
        last_seen = parse_time(event.get("eventTime"))
    if last_seen is None:
        last_seen = parse_time(metadata.get("creationTimestamp"))

    count = series.get("count") or event.get("count") or 1
    kind = str(involved.get("kind", "")).lower()
    name = str(involved.get("name", ""))
    return WarningEvent(
        last_seen=last_seen,
        object=f"{kind}/{name}",
        reason=str(event.get("reason", "")),
        message=str(event.get("message", "")).strip(),
        count=int(count),
    )


def usage(metrics: SmarterDictType) -> tuple[Optional[float], Optional[int]]:
    """
    Read the CPU and memory in use from one metrics-server item, as ``kubectl top`` shows them.

    :param metrics: A ``pods.metrics.k8s.io`` item, whose ``containers`` each have a ``usage``, which
        are added up, or a ``nodes.metrics.k8s.io`` item, which has one ``usage``.
    :returns: The cores and the bytes in use. Either is None if the item does not report it.
    """
    if "containers" in metrics:
        usages = []
        for container in metrics.get("containers") or []:
            usages.append(section(container, "usage"))
    else:
        usages = [section(metrics, "usage")]
    cpu = total_cores(parse_cpu(item.get("cpu")) for item in usages)
    memory = total_bytes(parse_memory(item.get("memory")) for item in usages)
    return cpu, memory


def usage_by_name(items: list[SmarterDictType]) -> dict[str, tuple[Optional[float], Optional[int]]]:
    """
    Index metrics-server's items by the name of their pod or node.

    :param items: The items of ``pods.metrics.k8s.io`` or ``nodes.metrics.k8s.io``.
    :returns: The cores and bytes in use of each pod or node, by its name, as :func:`usage` reads them.
    """
    result = {}
    for item in items:
        name = str(section(item, "metadata").get("name", ""))
        result[name] = usage(item)
    return result


def read_pods(snapshot: ClusterSnapshot) -> None:
    """
    Add the namespace's pods, and the CPU and memory that each one uses, to a snapshot.

    A Job's pod that finished successfully, e.g. the nightly database backup's, is left out: it is
    not running, and nothing is wrong with it. A pod that metrics-server does not report, e.g. one
    that has just started, has no use.

    Side effects: two ``kubectl get`` calls, for ``pod`` and ``pods.metrics.k8s.io``, in the
    snapshot's namespace. Nothing is written.

    :param snapshot: The snapshot, whose :attr:`~ClusterSnapshot.pods` this fills, and to whose
        :attr:`~ClusterSnapshot.errors` it adds a part that cannot be read.
    """
    kubernetes = infrastructure.kubernetes
    pods = kubernetes.find_resources("pod", snapshot.namespace)
    if pods is None:
        snapshot.errors.append("pods: the cluster could not be read")
        return
    for pod in pods:
        if section(pod, "status").get("phase") == "Succeeded":
            continue
        snapshot.pods.append(pod_status(pod))
    snapshot.pods.sort(key=lambda pod: (pod.component, pod.name))

    metrics = kubernetes.find_resources("pods.metrics.k8s.io", snapshot.namespace)
    if metrics is None:
        snapshot.errors.append("pod metrics: metrics-server could not be read")
        return
    in_use = usage_by_name(metrics)
    for pod in snapshot.pods:
        pod.cpu, pod.memory = in_use.get(pod.name, (None, None))


def read_nodes(snapshot: ClusterSnapshot) -> None:
    """
    Add the cluster's nodes, and the CPU and memory that each one uses, to a snapshot.

    The nodes are shared by every environment of the cluster, so they are read cluster-wide, not in
    the snapshot's namespace.

    Side effects: two ``kubectl get`` calls, for ``node`` and ``nodes.metrics.k8s.io``. Nothing is
    written.

    :param snapshot: The snapshot, whose :attr:`~ClusterSnapshot.nodes` this fills, and to whose
        :attr:`~ClusterSnapshot.errors` it adds a part that cannot be read.
    """
    kubernetes = infrastructure.kubernetes
    nodes = kubernetes.find_resources("node")
    if nodes is None:
        snapshot.errors.append("nodes: the cluster could not be read")
        return
    for node in nodes:
        snapshot.nodes.append(node_status(node))
    snapshot.nodes.sort(key=lambda node: node.name)

    metrics = kubernetes.find_resources("nodes.metrics.k8s.io")
    if metrics is None:
        snapshot.errors.append("node metrics: metrics-server could not be read")
        return
    in_use = usage_by_name(metrics)
    for node in snapshot.nodes:
        node.cpu, node.memory = in_use.get(node.name, (None, None))


def read_events(snapshot: ClusterSnapshot, minutes: int) -> None:
    """
    Add the namespace's warning events of the last minutes to a snapshot, newest first.

    Events of type ``Normal``, e.g. a pulled image, are left out. Kubernetes keeps events for about an
    hour, so a period longer than that finds no older ones. An event that does not say when it last
    happened is kept, rather than hidden.

    Side effects: one ``kubectl get`` call, for ``event``, in the snapshot's namespace. Nothing is
    written.

    :param snapshot: The snapshot, whose :attr:`~ClusterSnapshot.events` this fills, and to whose
        :attr:`~ClusterSnapshot.errors` it adds the events if they cannot be read.
    :param minutes: How far back to keep events, in minutes.
    """
    events = infrastructure.kubernetes.find_resources("event", snapshot.namespace)
    if events is None:
        snapshot.errors.append("events: the cluster could not be read")
        return
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    for event in events:
        if event.get("type") != "Warning":
            continue
        warning = warning_event(event)
        if warning.last_seen is not None and warning.last_seen < since:
            continue
        snapshot.events.append(warning)
    snapshot.events.sort(key=lambda event: event.last_seen or since, reverse=True)


def cluster_snapshot(namespace: str, minutes: int = 60) -> ClusterSnapshot:
    """
    Read the environment's pods, the cluster's nodes, and the namespace's warning events, now.

    Each part is read on its own: one that fails is named in the snapshot's
    :attr:`~ClusterSnapshot.errors`, and the others are still read. It never raises for a cluster that
    cannot be reached.

    Side effects: five ``kubectl get`` calls through
    :data:`smarter.apps.infrastructure.services.infrastructure` ``.kubernetes`` (see
    :func:`read_pods`, :func:`read_nodes` and :func:`read_events`), each of which may first fetch a
    cluster token from the cloud provider. Nothing is written, and nothing is cached.

    :param namespace: The environment's namespace, e.g. ``smarter_settings.environment_namespace``.
    :param minutes: How far back to read warning events, in minutes.
    :returns: The snapshot.
    """
    snapshot = ClusterSnapshot(namespace=namespace)
    read_pods(snapshot)
    read_nodes(snapshot)
    read_events(snapshot, minutes)
    return snapshot


__all__ = [
    "ClusterSnapshot",
    "NodeStatus",
    "PodStatus",
    "WarningEvent",
    "cluster_snapshot",
    "mebibytes",
    "parse_cpu",
    "parse_memory",
    "percent",
]
