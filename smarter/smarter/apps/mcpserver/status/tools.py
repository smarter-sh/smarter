"""
The operations tools that report the platform's health now: ``platform_status`` and ``eks_status``.

They are tools of the Smarter Operations MCP server
(:mod:`smarter.apps.mcpserver.protocol.operations_server`), for the platform's staff and their AI
agents, e.g. Claude Code answering a help desk question.

- **platform_status** (:class:`PlatformStatusTool`) answers "is something wrong right now?" in one call.
  It reads the environment's pods and the cluster's nodes, with their CPU and memory use, the
  namespace's warning events (:mod:`~smarter.apps.mcpserver.status.cluster`), the dashboard's health
  checks, the Celery queues and the database's load (:mod:`~smarter.apps.mcpserver.status.platform`),
  and the status pages of the AI providers and of AWS (:mod:`~smarter.apps.mcpserver.status.feeds`).
  Its result starts with its *observations*: what looks wrong, in plain sentences, so that the LLM
  does not have to find it in the tables.
- **eks_status** (:class:`EksStatusTool`) reports the cluster as the cloud provider sees it: the control
  plane, the node groups, the add-ons and their available updates, and the provider's insights, e.g.
  readiness for the next Kubernetes version, from
  :meth:`~smarter.apps.infrastructure.providers.base.CloudProvider.get_kubernetes_cluster_health`.

Like every operations tool, each call takes a ``ticket``, is recorded in the audit trail, and is never
cached (see :class:`~smarter.apps.mcpserver.protocol.operations_tools.SmarterOperationsTool`). Nothing
adds cloud monitoring costs: the data comes from Kubernetes, metrics-server, the platform's own
services, the EKS api, and public status pages.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from smarter.apps.infrastructure.cluster_health import ClusterHealth
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.mcpserver.protocol.operations_tools import (
    UNTRUSTED_DATA_NOTICE,
    OperationsToolArguments,
    SmarterOperationsTool,
)
from smarter.apps.mcpserver.status.cluster import (
    ClusterSnapshot,
    NodeStatus,
    PodStatus,
    cluster_snapshot,
    mebibytes,
    percent,
)
from smarter.apps.mcpserver.status.feeds import (
    AwsEvent,
    ProviderStatus,
    aws_service_events,
    provider_statuses,
)
from smarter.apps.mcpserver.status.platform import (
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

MAX_EVENTS = 15
"""The most Kubernetes warning events that ``platform_status`` lists.

The observations count them all.
"""

MAX_EVENT_MESSAGE = 300
"""The most characters of a warning event's message that ``platform_status`` shows."""


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
    Format a time for a tool's result.

    :param value: The time, or None if it is unknown.
    :returns: The time in UTC, e.g. ``2026-11-02 14:05:00 UTC``, or ``?`` if it is unknown.
    """
    if value is None:
        return "?"
    in_utc = value.astimezone(timezone.utc)
    return f"{in_utc:%Y-%m-%d %H:%M:%S} UTC"


def pod_observations(pods: list[PodStatus]) -> list[str]:
    """
    Describe what is wrong with the environment's pods.

    A pod is an observation when it is not ready, reports a problem, e.g. ``CrashLoopBackOff``, has
    restarted, or uses at least :data:`HIGH_USE_PERCENT` of its memory limit.

    :param pods: The pods, from :func:`~smarter.apps.mcpserver.status.cluster.cluster_snapshot`.
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

    :param nodes: The nodes, from :func:`~smarter.apps.mcpserver.status.cluster.cluster_snapshot`.
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

    :param checks: The dashboard's health checks, from :func:`~smarter.apps.mcpserver.status.platform.health_checks`.
    :param depths: The Celery queues' depths, from :func:`~smarter.apps.mcpserver.status.platform.queue_depths`.
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
    the result's upstream section says so.

    :param providers: The AI providers' status, from :func:`~smarter.apps.mcpserver.status.feeds.provider_statuses`.
    :param aws_events: The recent AWS events, from :func:`~smarter.apps.mcpserver.status.feeds.aws_service_events`.
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
    Describe everything that looks wrong, for the top of ``platform_status``'s result.

    It gathers the observations of the pods, the nodes, the warning events, the backing services and
    the upstream status pages, and the parts of the cluster that could not be read.

    :param snapshot: The pods, nodes and warning events, from :func:`~smarter.apps.mcpserver.status.cluster.cluster_snapshot`.
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


def pods_table(pods: list[PodStatus]) -> list[str]:
    """
    Format the environment's pods as a Markdown table.

    :param pods: The pods.
    :returns: The table's lines: its header, then one row per pod, with its component, name, ready
        containers, restarts, problem, CPU use in cores, and memory use with its share of the pod's limit.
    """
    lines = [
        "| component | pod | ready | restarts | problem | CPU | memory (of limit) |",
        "|---|---|---|---|---|---|---|",
    ]
    for pod in pods:
        ready = f"{pod.ready_containers}/{pod.containers}"
        cpu = "?" if pod.cpu is None else f"{pod.cpu:.2f}"
        memory = mebibytes(pod.memory)
        memory_use = percent(pod.memory, pod.memory_limit)
        if memory_use is not None:
            memory += f" ({memory_use}%)"
        lines.append(f"| {pod.component} | {pod.name} | {ready} | {pod.restarts} | {pod.problem} | {cpu} | {memory} |")
    return lines


def nodes_table(nodes: list[NodeStatus]) -> list[str]:
    """
    Format the cluster's nodes as a Markdown table.

    :param nodes: The nodes.
    :returns: The table's lines: its header, then one row per node, with its name, readiness,
        instance type and capacity type, CPU and memory use as shares of what pods may use, and its
        pressure conditions, and whether it is cordoned.
    """
    lines = [
        "| node | ready | type | CPU use | memory use | conditions |",
        "|---|---|---|---|---|---|",
    ]
    for node in nodes:
        ready = "yes" if node.ready else "NO"
        kind = node.instance_type
        if node.capacity_type:
            kind += f" {node.capacity_type.lower()}"
        cpu_use = percent(node.cpu, node.cpu_allocatable)
        cpu = "?" if cpu_use is None else f"{cpu_use}%"
        memory_use = percent(node.memory, node.memory_allocatable)
        memory = "?" if memory_use is None else f"{memory_use}%"
        conditions = list(node.pressures)
        if node.unschedulable:
            conditions.append("cordoned")
        lines.append(f"| {node.name} | {ready} | {kind} | {cpu} | {memory} | {', '.join(conditions)} |")
    return lines


class PlatformStatusArguments(OperationsToolArguments):
    """The arguments of ``platform_status``: the ticket, and how far back to read warning events."""

    minutes: int = Field(
        default=60, ge=5, le=24 * 60, description="How far back to read Kubernetes warning events, in minutes."
    )


class PlatformStatusTool(SmarterOperationsTool):
    """
    The ``platform_status`` operations tool: the platform's health, now, in one call.

    **Reads:**

    - the environment's pods, the cluster's nodes, their CPU and memory use, and the namespace's
      warning events (:func:`~smarter.apps.mcpserver.status.cluster.cluster_snapshot`),
    - the dashboard's health checks, the Celery queues and the database's load
      (:mod:`smarter.apps.mcpserver.status.platform`),
    - the AI providers' and AWS's status pages (:mod:`smarter.apps.mcpserver.status.feeds`).

    **Result:** Markdown, which starts with the untrusted data notice, then the observations, then a
    section for each of the parts above. A part that cannot be read is named, and the others are still
    reported.

    **Side effects:** five ``kubectl get`` calls, a ``SELECT 1`` and two ``SHOW`` queries on the
    database, a value written to and deleted from the cache, a ping of the Celery workers, a connection
    to the Celery broker, and up to five HTTPS GETs of public status pages, which are cached for a
    minute. Nothing in the cluster, the database or the queues is changed.
    """

    name = "platform_status"
    title = "Platform status"
    description = (
        "Report the platform's health now, in one call: what looks wrong; the environment's pods (ready, restarts, "
        "problems such as CrashLoopBackOff or OOMKilled, CPU and memory use); the cluster's nodes (ready, pressure, "
        "CPU and memory use); recent Kubernetes warning events; the health checks of the database, cache, task "
        "broker and workers; the Celery queues' backlog; the database's connections; and the public status pages "
        "of the AI providers (OpenAI, Anthropic, Mistral) and of AWS EKS and EC2 in the platform's region. Call it "
        "first for 'is Smarter down?', 'why is it slow?' and 'is something wrong with EKS?'."
    )
    arguments_model = PlatformStatusArguments
    open_world = True

    def run(self, arguments: PlatformStatusArguments) -> str:  # type: ignore[override]
        """
        Read the platform's health, and report it.

        :param arguments: The validated arguments: the ticket, and the minutes of warning events to read.
        :returns: The report, as Markdown.
        """
        namespace = smarter_settings.environment_namespace
        region = platform_region()
        snapshot = cluster_snapshot(namespace, minutes=arguments.minutes)
        checks = health_checks()
        depths = queue_depths()
        database = self.read_database()
        providers = provider_statuses()
        aws_events, unread_feeds = aws_service_events(region)
        found = observations(snapshot, checks, depths, database, providers, aws_events)

        now = utc(datetime.now(timezone.utc))
        out = [UNTRUSTED_DATA_NOTICE + f"## Platform status of {namespace}, {now}", ""]
        out += self.observations_section(found)
        out += ["", "### Pods", ""]
        out += pods_table(snapshot.pods)
        out += ["", "### Nodes (shared by every environment of the cluster)", ""]
        out += nodes_table(snapshot.nodes)
        out += ["", f"### Kubernetes warning events in the last {arguments.minutes} minutes", ""]
        out += self.events_section(snapshot)
        out += ["", "### Services", ""]
        out += self.services_section(checks, depths, database)
        out += ["", "### Upstream status pages", ""]
        out += self.upstream_section(providers, aws_events, unread_feeds, region)
        return "\n".join(out)

    def read_database(self) -> Optional[DatabaseLoad]:
        """
        Read the database's load, or report that it could not be read.

        :returns: The load, or None if the database could not be queried. The failure is logged, and
            becomes an observation.
        """
        try:
            return database_load()
        # pylint: disable=broad-except
        except Exception as e:
            logger.warning(
                "%s.PlatformStatusTool.read_database() could not read the database's load: %s", logger_prefix, e
            )
            return None

    @staticmethod
    def observations_section(found: list[str]) -> list[str]:
        """
        Format the observations section.

        :param found: The observations, from :func:`observations`.
        :returns: The section's lines: one bullet per observation, or one that says nothing looks wrong.
        """
        lines = ["### Observations", ""]
        if not found:
            lines.append("- Nothing looks wrong.")
            return lines
        for observation in found:
            lines.append(f"- {observation}")
        return lines

    @staticmethod
    def events_section(snapshot: ClusterSnapshot) -> list[str]:
        """
        Format the warning events section.

        :param snapshot: The snapshot, whose events are newest first.
        :returns: The section's lines: one bullet per event, at most :data:`MAX_EVENTS`, each with its
            time, object, reason, count and message, cut at :data:`MAX_EVENT_MESSAGE` characters, or
            one that says there are none.
        """
        if not snapshot.events:
            return ["- None."]
        lines = []
        for event in snapshot.events[:MAX_EVENTS]:
            message = event.message[:MAX_EVENT_MESSAGE]
            lines.append(f"- {utc(event.last_seen)} {event.object} {event.reason} (×{event.count}): {message}")
        return lines

    @staticmethod
    def services_section(
        checks: list[tuple[str, bool]],
        depths: dict[str, Optional[int]],
        database: Optional[DatabaseLoad],
    ) -> list[str]:
        """
        Format the backing services section.

        :param checks: The dashboard's health checks.
        :param depths: The Celery queues' depths.
        :param database: The database's load, or None if it could not be read.
        :returns: The section's lines: one bullet per health check, per queue, and for the database.
        """
        lines = []
        for name, healthy in checks:
            state = "healthy" if healthy else "FAILED"
            lines.append(f"- {name}: {state}")
        for queue, depth in depths.items():
            waiting = "unknown" if depth is None else f"{depth} waiting"
            lines.append(f"- Celery queue {queue}: {waiting}")
        if database is None:
            lines.append("- Database: its load could not be read")
            return lines
        lines.append(
            f"- Database: {database.connections} of {database.max_connections} connections, "
            f"{database.running} running, {database.slow_queries} slow queries since it started"
        )
        return lines

    @staticmethod
    def upstream_section(
        providers: list[ProviderStatus], aws_events: list[AwsEvent], unread_feeds: list[str], region: str
    ) -> list[str]:
        """
        Format the upstream status pages section.

        :param providers: The AI providers' status.
        :param aws_events: The recent AWS events. They are listed in the observations.
        :param unread_feeds: The AWS services whose feed could not be read.
        :param region: The platform's AWS region.
        :returns: The section's lines: one bullet per AI provider, one per unread AWS feed, and one that
            says AWS reports no events, when it does not.
        """
        lines = []
        for provider in providers:
            lines.append(f"- {provider.name}: {provider.description} ({provider.url})")
        for service in unread_feeds:
            lines.append(f"- AWS {service}: could not be read")
        if not aws_events and not unread_feeds:
            lines.append(f"- AWS EKS and EC2 in {region}: no events in the last 3 days")
        return lines


class EksStatusTool(SmarterOperationsTool):
    """
    The ``eks_status`` operations tool: the cluster, as the cloud provider sees it.

    **Reads:** :meth:`~smarter.apps.infrastructure.providers.base.CloudProvider.get_kubernetes_cluster_health`,
    i.e. for AWS, the EKS cluster, its node groups, its add-ons and their newest versions, and EKS's
    insights, and the recent events of AWS EKS and EC2 in the platform's region
    (:func:`~smarter.apps.mcpserver.status.feeds.aws_service_events`).

    **Result:** Markdown: the control plane, then a section each for the node groups, the add-ons, the
    insights that are not passing, and the AWS events. A part that could not be read, e.g. insights,
    which need the ``eks:ListInsights`` permission, is named, and the others are still reported. A
    cloud provider that is not ready, e.g. in local development, makes the call a tool error.

    **Side effects:** read-only calls to the EKS api (``DescribeCluster``, ``ListNodegroups``,
    ``DescribeNodegroup``, ``ListAddons``, ``DescribeAddon``, ``DescribeAddonVersions`` and
    ``ListInsights``), and up to two HTTPS GETs of AWS status feeds, which are cached for a minute.
    """

    name = "eks_status"
    title = "EKS status"
    description = (
        "Report the platform's Kubernetes cluster as AWS EKS sees it: the control plane's status, version and "
        "health issues; each node group's status, size, instance types and health issues; each add-on's version, "
        "health issues and whether a newer version is available; EKS's insights, e.g. readiness for the next "
        "Kubernetes version; and the recent events of AWS EKS and EC2 in the platform's region."
    )
    arguments_model = OperationsToolArguments
    open_world = True

    def run(self, arguments: OperationsToolArguments) -> str:
        """
        Read the cluster's health from the cloud provider, and report it.

        :param arguments: The validated arguments: the ticket.
        :returns: The report, as Markdown.
        :raises InfrastructureNotReadyError: If the cloud provider is not ready.
        :raises SmarterInfrastructureError: If the cluster cannot be described.
        """
        health = infrastructure.provider.get_kubernetes_cluster_health()
        region = platform_region()
        aws_events, unread_feeds = aws_service_events(region)

        out = [f"## Cluster {health.name}", ""]
        out += self.control_plane_section(health)
        out += ["", "### Node groups", ""]
        out += self.nodegroups_section(health)
        out += ["", "### Add-ons", ""]
        out += self.addons_section(health)
        out += ["", "### Insights", ""]
        out += self.insights_section(health)
        out += ["", f"### AWS events in {region}, last 3 days", ""]
        out += self.aws_section(aws_events, unread_feeds)
        return "\n".join(out)

    @staticmethod
    def control_plane_section(health: ClusterHealth) -> list[str]:
        """
        Format the control plane's status, version and health issues.

        :param health: The cluster's health.
        :returns: The section's lines.
        """
        status = health.status or "?"
        version = health.version or "?"
        lines = [f"- Control plane: {status}, Kubernetes {version}, platform version {health.platform_version or '?'}"]
        if not health.issues:
            lines.append("- No control plane health issues.")
            return lines
        for issue in health.issues:
            lines.append(f"- Control plane issue {issue.code}: {issue.message}")
        return lines

    @staticmethod
    def nodegroups_section(health: ClusterHealth) -> list[str]:
        """
        Format the node groups: each one's status, size, instances, node image and health issues.

        :param health: The cluster's health.
        :returns: The section's lines, or one that says none is listed.
        """
        if not health.nodegroups:
            return ["- None listed."]
        lines = []
        for group in health.nodegroups:
            size = f"{group.desired_size} nodes (min {group.min_size}, max {group.max_size})"
            instances = ", ".join(group.instance_types)
            capacity = group.capacity_type.lower()
            image = group.release_version or "?"
            lines.append(f"- {group.name}: {group.status}, {size}, {instances} {capacity}, image {image}")
            for issue in group.issues:
                lines.append(f"  - issue {issue.code}: {issue.message} ({len(issue.resources)} resources)")
        return lines

    @staticmethod
    def addons_section(health: ClusterHealth) -> list[str]:
        """
        Format the add-ons: each one's version, status, available update and health issues.

        :param health: The cluster's health.
        :returns: The section's lines, or one that says none is listed.
        """
        if not health.addons:
            return ["- None listed."]
        lines = []
        for addon in health.addons:
            update = ""
            if addon.update_available:
                update = f", update available: {addon.latest_version}"
            lines.append(f"- {addon.name} {addon.version}: {addon.status}{update}")
            for issue in addon.issues:
                lines.append(f"  - issue {issue.code}: {issue.message}")
        return lines

    @staticmethod
    def insights_section(health: ClusterHealth) -> list[str]:
        """
        Format the insights that need attention, count those that pass, and name the parts that could not be read.

        :param health: The cluster's health.
        :returns: The section's lines.
        """
        lines = []
        passing = 0
        for insight in health.insights:
            if insight.status == "PASSING":
                passing += 1
                continue
            line = f"- {insight.status} {insight.category} {insight.name}"
            if insight.kubernetes_version:
                line += f" (Kubernetes {insight.kubernetes_version})"
            if insight.reason:
                line += f": {insight.reason}"
            lines.append(line)
        if health.insights:
            lines.append(f"- {passing} insights are passing.")
        else:
            lines.append("- None listed.")
        for error in health.errors:
            lines.append(f"- Could not read {error}.")
        return lines

    @staticmethod
    def aws_section(aws_events: list[AwsEvent], unread_feeds: list[str]) -> list[str]:
        """
        Format the recent AWS events.

        :param aws_events: The events, newest first.
        :param unread_feeds: The AWS services whose feed could not be read.
        :returns: The section's lines, or one that says there are none.
        """
        lines = []
        for event in aws_events:
            lines.append(f"- {utc(event.published)} {event.service}: {event.title}")
        for service in unread_feeds:
            lines.append(f"- AWS {service}: the status feed could not be read")
        if not lines:
            lines.append("- None.")
        return lines


__all__ = ["EksStatusTool", "PlatformStatusTool", "observations"]
