"""
The platform's health now, in one report: everything that the status services read, and what looks wrong.

- :func:`platform_status` reads the environment's pods and the cluster's nodes, with their CPU and
  memory use, the namespace's warning events (:mod:`~smarter.apps.mcpserver.services.status.cluster`),
  the dashboard's health checks, the Celery queues and the database's load
  (:mod:`~smarter.apps.mcpserver.services.status.platform`), and the status pages of the AI
  providers and of AWS (:mod:`~smarter.apps.mcpserver.services.status.feeds`). Its report starts
  with its *observations*: what looks wrong, in plain sentences, from :func:`observations`.
- :func:`eks_status` reads the cluster as the cloud provider sees it: the control plane, the node
  groups, the add-ons and their available updates, and the provider's insights, from
  :meth:`~smarter.apps.infrastructure.providers.base.CloudProvider.get_kubernetes_cluster_health`,
  and the recent AWS events of the platform's region.

The MCPServer's staff-only tools ``platform_status`` and ``eks_status``
(:mod:`smarter.apps.mcpserver.protocol.tools.status`) format these reports as Markdown. Nothing
adds cloud monitoring costs: the data comes from Kubernetes, metrics-server, the platform's own
services, the EKS api, and public status pages.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from smarter.apps.infrastructure.cluster_health import ClusterHealth
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.mcpserver.services.status.cluster import (
    ClusterSnapshot,
    NodeStatus,
    PodStatus,
    cluster_snapshot,
    percent,
)
from smarter.apps.mcpserver.services.status.feeds import (
    AwsEvent,
    ProviderStatus,
    aws_service_events,
    provider_statuses,
)
from smarter.apps.mcpserver.services.status.platform import (
    DatabaseLoad,
    database_load,
    health_checks,
    queue_depths,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

HIGH_USE_PERCENT = 90
"""
The use, as a percentage of what is allowed, at which a pod's memory, or a node's CPU or memory, is an observation.

A pod above its memory limit is killed (``OOMKilled``), and a node that is full cannot take new pods.
"""

DATABASE_BUSY_PERCENT = 80
"""The share of the database's connection limit in use at which the database is an observation."""

QUEUE_BACKLOG = 50
"""The number of tasks waiting in a Celery queue at which the queue is an observation: the workers are behind."""


def platform_region() -> str:
    """
    Return the platform's AWS region, for the AWS status feeds and the report.

    ``smarter_settings.aws_region`` is None when no region is configured. It is then reported, and
    put in the feeds' urls, as ``None``, as the tools have always done. No AWS feed exists for a
    region of that name.

    :returns: The region, e.g. ``us-east-2``, or ``"None"`` if none is configured.
    """
    region = smarter_settings.aws_region
    if region is None:
        return "None"
    return region


def utc(value: Optional[datetime]) -> str:
    """
    Format a time for a report.

    :param value: The time, or None if it is unknown.
    :returns: The time in UTC, e.g. ``2026-11-02 14:05:00 UTC``, or ``?`` if it is unknown.
    """
    if value is None:
        return "?"
    in_utc = value.astimezone(timezone.utc)
    formatted = f"{in_utc:%Y-%m-%d %H:%M:%S} UTC"
    return formatted


def pod_observations(pods: list[PodStatus]) -> list[str]:
    """
    Describe what is wrong with the environment's pods.

    A pod is an observation when it is not ready, reports a problem, e.g. ``CrashLoopBackOff``, has
    restarted, or uses at least :data:`HIGH_USE_PERCENT` of its memory limit.

    :param pods: The pods, from :func:`~smarter.apps.mcpserver.services.status.cluster.cluster_snapshot`.
    :returns: One sentence per problem, or an empty list if there is none.
    """
    found = []
    for pod in pods:
        if not pod.ready or pod.problem:
            reason = pod.problem or pod.phase or "not ready"
            found.append(f"Pod {pod.name} ({pod.component}) is not healthy: {reason}.")
        elif pod.restarts:
            found.append(f"Pod {pod.name} ({pod.component}) has restarted {pod.restarts} times since it was created.")
        memory_use = percent(pod.memory, pod.memory_limit)
        if memory_use is not None and memory_use >= HIGH_USE_PERCENT:
            found.append(
                f"Pod {pod.name} uses {memory_use}% of its memory limit, and may be killed for lack of memory."
            )
    return found


def node_observations(nodes: list[NodeStatus]) -> list[str]:
    """
    Describe what is wrong with the cluster's nodes.

    A node is an observation when it is not ready, reports a pressure condition, e.g.
    ``MemoryPressure``, is cordoned, or uses at least :data:`HIGH_USE_PERCENT` of its CPU or memory.

    :param nodes: The nodes, from :func:`~smarter.apps.mcpserver.services.status.cluster.cluster_snapshot`.
    :returns: One sentence per problem, or an empty list if there is none.
    """
    found = []
    for node in nodes:
        if not node.ready:
            found.append(f"Node {node.name} is not ready.")
        if node.pressures:
            pressures = ", ".join(node.pressures)
            found.append(f"Node {node.name} reports {pressures}.")
        if node.unschedulable:
            found.append(f"Node {node.name} is cordoned: no new pods are scheduled on it.")
        cpu_use = percent(node.cpu, node.cpu_allocatable)
        if cpu_use is not None and cpu_use >= HIGH_USE_PERCENT:
            found.append(f"Node {node.name} uses {cpu_use}% of its CPU.")
        memory_use = percent(node.memory, node.memory_allocatable)
        if memory_use is not None and memory_use >= HIGH_USE_PERCENT:
            found.append(f"Node {node.name} uses {memory_use}% of its memory.")
    return found


def service_observations(
    checks: list[tuple[str, bool]],
    depths: dict[str, Optional[int]],
    database: Optional[DatabaseLoad],
) -> list[str]:
    """
    Describe what is wrong with the platform's backing services.

    A failed health check is an observation, and so is a Celery queue that could not be read or has at
    least :data:`QUEUE_BACKLOG` waiting tasks, and a database with at least
    :data:`DATABASE_BUSY_PERCENT` of its connections in use.

    :param checks: The dashboard's health checks, from :func:`~smarter.apps.mcpserver.services.status.platform.health_checks`.
    :param depths: The Celery queues' depths, from :func:`~smarter.apps.mcpserver.services.status.platform.queue_depths`.
    :param database: The database's load, or None if it could not be read.
    :returns: One sentence per problem, or an empty list if there is none.
    """
    found = []
    for name, healthy in checks:
        if not healthy:
            found.append(f"The {name} health check failed.")
    for queue, depth in depths.items():
        if depth is None:
            found.append(f"The Celery queue {queue} could not be read.")
        elif depth >= QUEUE_BACKLOG:
            found.append(f"{depth} tasks are waiting in the Celery queue {queue}: the workers are behind.")
    if database is None:
        found.append("The database's load could not be read.")
        return found
    connection_use = percent(database.connections, database.max_connections)
    if connection_use is not None and connection_use >= DATABASE_BUSY_PERCENT:
        found.append(f"The database has {database.connections} of {database.max_connections} connections in use.")
    return found


def upstream_observations(providers: list[ProviderStatus], aws_events: list[AwsEvent]) -> list[str]:
    """
    Describe the problems that the AI providers and AWS report on their status pages.

    A provider whose page could not be read is not an observation: its status is unknown, not bad, and
    the report's upstream section says so.

    :param providers: The AI providers' status, from :func:`~smarter.apps.mcpserver.services.status.feeds.provider_statuses`.
    :param aws_events: The recent AWS events, from :func:`~smarter.apps.mcpserver.services.status.feeds.aws_service_events`.
    :returns: One sentence per problem, or an empty list if there is none.
    """
    found = []
    for provider in providers:
        if provider.operational:
            continue
        if provider.indicator == "unknown":
            continue
        found.append(f"{provider.name} reports {provider.description or provider.indicator} ({provider.url}).")
    for event in aws_events:
        found.append(f"AWS {event.service} event: {event.title} ({utc(event.published)}).")
    return found


def observations(
    snapshot: ClusterSnapshot,
    checks: list[tuple[str, bool]],
    depths: dict[str, Optional[int]],
    database: Optional[DatabaseLoad],
    providers: list[ProviderStatus],
    aws_events: list[AwsEvent],
) -> list[str]:
    """
    Describe everything that looks wrong, for the top of the platform's status report.

    It gathers the observations of the pods, the nodes, the warning events, the backing services and
    the upstream status pages, and the parts of the cluster that could not be read.

    :param snapshot: The pods, nodes and warning events, from :func:`~smarter.apps.mcpserver.services.status.cluster.cluster_snapshot`.
    :param checks: The dashboard's health checks.
    :param depths: The Celery queues' depths.
    :param database: The database's load, or None if it could not be read.
    :param providers: The AI providers' status.
    :param aws_events: The recent AWS events.
    :returns: One sentence per problem, or an empty list if nothing looks wrong.
    """
    found = []
    found += pod_observations(snapshot.pods)
    found += node_observations(snapshot.nodes)
    if snapshot.events:
        found.append(f"{len(snapshot.events)} Kubernetes warning events in the period.")
    found += service_observations(checks, depths, database)
    found += upstream_observations(providers, aws_events)
    for error in snapshot.errors:
        found.append(f"Could not read {error}.")
    return found


def read_database() -> Optional[DatabaseLoad]:
    """
    Read the database's load, or report that it could not be read.

    :returns: The load, or None if the database could not be queried. The failure is logged, and
        becomes an observation.
    """
    try:
        return database_load()
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("%s.read_database() could not read the database's load: %s", logger_prefix, e)
        return None


@dataclass(frozen=True)
class PlatformStatus:
    """The platform's health now, as :func:`platform_status` returns it."""

    namespace: str
    """The environment's Kubernetes namespace."""

    region: str
    """The platform's AWS region, from :func:`platform_region`."""

    snapshot: ClusterSnapshot
    """The environment's pods, the cluster's nodes, and the namespace's warning events."""

    checks: list[tuple[str, bool]]
    """The dashboard's health checks: each one's name, and whether it passed."""

    depths: dict[str, Optional[int]]
    """The number of tasks waiting in each Celery queue, or None for a queue that could not be read."""

    database: Optional[DatabaseLoad]
    """The database's load, or None if it could not be read."""

    providers: list[ProviderStatus]
    """The AI providers' status pages."""

    aws_events: list[AwsEvent]
    """The recent AWS events of EKS and EC2 in the region."""

    unread_feeds: list[str]
    """The AWS services whose status feed could not be read."""

    observations: list[str]
    """What looks wrong, in plain sentences, from :func:`observations`."""


def platform_status(minutes: int) -> PlatformStatus:
    """
    Read the platform's health now, and what looks wrong.

    **Side effects:** five ``kubectl get`` calls, a ``SELECT 1`` and two ``SHOW`` queries on the
    database, a value written to and deleted from the cache, a ping of the Celery workers, a connection
    to the Celery broker, and up to five HTTPS GETs of public status pages, which are cached for a
    minute. Nothing in the cluster, the database or the queues is changed.

    :param minutes: How far back to read Kubernetes warning events.
    :returns: Everything that was read, and the observations. A part that cannot be read is named in
        the observations, and the others are still read.
    """
    namespace = smarter_settings.environment_namespace
    region = platform_region()
    snapshot = cluster_snapshot(namespace, minutes=minutes)
    checks = health_checks()
    depths = queue_depths()
    database = read_database()
    providers = provider_statuses()
    aws_events, unread_feeds = aws_service_events(region)
    found = observations(snapshot, checks, depths, database, providers, aws_events)
    status = PlatformStatus(
        namespace=namespace,
        region=region,
        snapshot=snapshot,
        checks=checks,
        depths=depths,
        database=database,
        providers=providers,
        aws_events=aws_events,
        unread_feeds=unread_feeds,
        observations=found,
    )
    return status


@dataclass(frozen=True)
class EksStatus:
    """The cluster, as the cloud provider sees it, as :func:`eks_status` returns it."""

    health: ClusterHealth
    """The cluster's control plane, node groups, add-ons and insights."""

    region: str
    """The platform's AWS region, from :func:`platform_region`."""

    aws_events: list[AwsEvent]
    """The recent AWS events of EKS and EC2 in the region."""

    unread_feeds: list[str]
    """The AWS services whose status feed could not be read."""


def eks_status() -> EksStatus:
    """
    Read the cluster's health from the cloud provider, and the recent AWS events of its region.

    **Side effects:** read-only calls to the EKS api (``DescribeCluster``, ``ListNodegroups``,
    ``DescribeNodegroup``, ``ListAddons``, ``DescribeAddon``, ``DescribeAddonVersions`` and
    ``ListInsights``), and up to two HTTPS GETs of AWS status feeds, which are cached for a minute.

    :returns: The cluster's health, and the region's AWS events.
    :raises InfrastructureNotReadyError: If the cloud provider is not ready.
    :raises SmarterInfrastructureError: If the cluster cannot be described.
    """
    health = infrastructure.provider.get_kubernetes_cluster_health()
    region = platform_region()
    aws_events, unread_feeds = aws_service_events(region)
    status = EksStatus(health=health, region=region, aws_events=aws_events, unread_feeds=unread_feeds)
    return status


__all__ = [
    "DATABASE_BUSY_PERCENT",
    "HIGH_USE_PERCENT",
    "QUEUE_BACKLOG",
    "EksStatus",
    "PlatformStatus",
    "eks_status",
    "node_observations",
    "observations",
    "platform_region",
    "platform_status",
    "pod_observations",
    "read_database",
    "service_observations",
    "upstream_observations",
    "utc",
]
