"""
Observability of LLMHosts: their status, health and cost.

- :func:`interpret` maps what Kubernetes reports about an LLMHost's Deployment and pods to
  an LLMHost status, e.g. an image that cannot be pulled is ``error``, and an init container
  that is copying weights is ``downloading``. It is a pure function, for testing.
- :class:`HealthProber` calls the engine's health endpoint.
- :func:`build_report` summarizes LLMHosts' status, GPUs and cost.
"""

import datetime
import os
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Iterable, Optional

import requests

from smarter.apps.llmhost.const import HEALTH_CHECK_TIMEOUT_SECONDS
from smarter.apps.llmhost.manifest.enum import SAMLLMHostStatusEnum
from smarter.lib.typing import SmarterDictType

if TYPE_CHECKING:
    from smarter.apps.llmhost.models import LLMHost

Status = SAMLLMHostStatusEnum

ERROR_REASONS = frozenset(
    [
        "ErrImagePull",
        "ImagePullBackOff",
        "InvalidImageName",
        "CrashLoopBackOff",
        "CreateContainerConfigError",
        "CreateContainerError",
        "RunContainerError",
    ]
)
"""Container waiting reasons that do not resolve without a change to the spec or the cluster."""


@dataclass
class LLMHostObservation:
    """
    What is known about an LLMHost, as of a status check.

    :param status: The LLMHost status, e.g. active.
    :param message: Why, e.g. a container error, or a pod that cannot be scheduled.
    :param replicas: The desired replicas.
    :param ready_replicas: The ready replicas.
    :param healthy: The result of the health check, or None if it was not checked.
    :param endpoint: The base URL inside the cluster.
    :param public_url: The base URL of the Ingress, if any.
    :param pods: A summary of each pod: name, phase, ready, restarts and reason.
    :param checked_at: When the status was checked.
    """

    status: str
    message: str = ""
    replicas: int = 0
    ready_replicas: int = 0
    healthy: Optional[bool] = None
    endpoint: Optional[str] = None
    public_url: Optional[str] = None
    pods: list[SmarterDictType] = field(default_factory=list)
    checked_at: Optional[datetime.datetime] = None

    def to_dict(self) -> SmarterDictType:
        """
        The observation, in camelCase, for JSON responses: :class:`~smarter.apps.llmhost.contract.models.LLMHostApiObservation`, dumped.

        :returns: The observation's JSON.
        :rtype: SmarterDictType
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmhost.contract.models import LLMHostApiObservation

        return LLMHostApiObservation.from_observation(self).model_dump(mode="json")


def summarize_pod(pod: SmarterDictType) -> SmarterDictType:
    """
    Summarize a pod: its name, phase, readiness, restarts, and the reason it is not ready, if any.

    :param pod: The pod, as a Kubernetes API dict.
    :returns: A dict with ``name``, ``phase``, ``ready``, ``restarts``, ``downloading`` (an init
        container, which copies the model weights, is running) and ``reason`` (None when there is
        nothing to report).
    """
    status = pod.get("status", {}) or {}
    containers = status.get("containerStatuses", []) or []
    init_containers = status.get("initContainerStatuses", []) or []
    reason = None
    for container in [*init_containers, *containers]:
        name = container.get("name")
        state = container.get("state", {}) or {}
        waiting = state.get("waiting")
        if waiting and waiting.get("reason") not in (None, "PodInitializing", "ContainerCreating"):
            waiting_reason = waiting.get("reason")
            waiting_message = waiting.get("message", "")
            reason = f"{name}: {waiting_reason}: {waiting_message}".strip(": ")
            break
        last_state = container.get("lastState", {}) or {}
        last = last_state.get("terminated")
        if last and last.get("reason") in ("OOMKilled", "Error"):
            reason = f"{name}: last terminated: {last.get('reason')}"
    if reason is None:
        conditions = status.get("conditions", []) or []
        for condition in conditions:
            if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
                condition_reason = condition.get("reason", "Unschedulable")
                condition_message = condition.get("message", "")
                reason = f"{condition_reason}: {condition_message}".strip(": ")

    ready = bool(containers) and all(c.get("ready") for c in containers)
    restarts = sum(int(c.get("restartCount", 0) or 0) for c in containers)
    downloading = False
    for init_container in init_containers:
        init_state = init_container.get("state", {}) or {}
        if "running" in init_state:
            downloading = True
            break
    summary = {
        "name": pod.get("metadata", {}).get("name"),
        "phase": status.get("phase"),
        "ready": ready,
        "restarts": restarts,
        "downloading": downloading,
        "reason": reason,
    }
    return summary


def _has_error(pod: SmarterDictType) -> Optional[str]:
    status = pod.get("status", {}) or {}
    init_containers = status.get("initContainerStatuses") or []
    containers = status.get("containerStatuses") or []
    for container in [*init_containers, *containers]:
        state = container.get("state", {}) or {}
        waiting = state.get("waiting") or {}
        if waiting.get("reason") in ERROR_REASONS:
            name = container.get("name")
            waiting_reason = waiting.get("reason")
            waiting_message = waiting.get("message", "")
            error = f"{name}: {waiting_reason}: {waiting_message}".strip(": ")
            return error
    return None


def _unschedulable(pod: SmarterDictType) -> Optional[str]:
    status = pod.get("status", {}) or {}
    conditions = status.get("conditions", []) or []
    for condition in conditions:
        if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
            condition_reason = condition.get("reason", "Unschedulable")
            condition_message = condition.get("message", "")
            message = f"{condition_reason}: {condition_message}".strip(": ")
            return message
    return None


# pylint: disable=too-many-return-statements
def interpret(deployment: Optional[SmarterDictType], pods: list[SmarterDictType]) -> tuple[str, str, int, int]:
    """
    Map an LLMHost's Deployment and pods to its status.

    :param deployment: The LLMHost's Deployment, as a Kubernetes API dict, or None if it has none.
    :param pods: The Deployment's pods, as Kubernetes API dicts.
    :returns: (status, message, desired replicas, ready replicas)
    """
    if not deployment:
        return Status.INACTIVE.value, "Not deployed.", 0, 0
    deployment_spec = deployment.get("spec", {}) or {}
    desired = int(deployment_spec.get("replicas", 1) or 0)
    dstatus = deployment.get("status", {}) or {}
    ready = int(dstatus.get("readyReplicas", 0) or 0)

    for condition in dstatus.get("conditions", []) or []:
        if condition.get("type") == "Progressing" and condition.get("reason") == "ProgressDeadlineExceeded":
            if ready == 0:
                return Status.ERROR.value, condition.get("message", "Progress deadline exceeded."), desired, ready

    errors = []
    for pod in pods:
        error = _has_error(pod)
        if error:
            errors.append(error)
    if desired and ready >= desired:
        return Status.ACTIVE.value, f"{ready}/{desired} replicas ready.", desired, ready
    if ready > 0:
        detail = f" {errors[0]}" if errors else ""
        return Status.DEGRADED.value, f"{ready}/{desired} replicas ready.{detail}", desired, ready
    if errors:
        return Status.ERROR.value, errors[0], desired, ready
    if any(summarize_pod(pod)["downloading"] for pod in pods):
        return Status.DOWNLOADING.value, "Copying the model weights to the model volume.", desired, ready
    unschedulable = []
    for pod in pods:
        unschedulable_reason = _unschedulable(pod)
        if unschedulable_reason:
            unschedulable.append(unschedulable_reason)
    if not pods or unschedulable:
        message = unschedulable[0] if unschedulable else "Waiting for pods to be created."
        return Status.PENDING.value, message, desired, ready
    return (
        Status.DEPLOYING.value,
        "Starting the inference server, and downloading and loading the weights.",
        desired,
        ready,
    )


def in_cluster() -> bool:
    """Whether Smarter is running in Kubernetes, and so can reach LLMHosts' Services."""
    return bool(os.environ.get("KUBERNETES_SERVICE_HOST"))


class HealthProber:
    """Calls an LLMHost's health endpoint inside the cluster."""

    def __init__(self, timeout: float = HEALTH_CHECK_TIMEOUT_SECONDS, enabled: Optional[bool] = None):
        self.timeout = timeout
        self.enabled = in_cluster() if enabled is None else enabled

    def check(self, url: str, api_key: Optional[str] = None) -> Optional[bool]:
        """
        Return whether ``url`` answers with a 2xx status.

        :returns: None if probing is disabled, i.e. outside the cluster, where Services are unreachable.
        """
        if not self.enabled or not url:
            return None
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            return 200 <= response.status_code < 300
        except requests.RequestException:
            return False


def build_report(llmhosts: Iterable["LLMHost"]) -> SmarterDictType:
    """
    Summarize LLMHosts: their count by status and engine, the GPUs they use, and their cost.

    The report is built as :class:`~smarter.apps.llmhost.contract.models.LLMHostApiReport`, which the
    api publishes, and returned as its JSON.

    :param llmhosts: LLMHost instances.
    :returns: The report's JSON.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.llmhost.contract.models import (
        LLMHostApiReport,
        LLMHostApiReportHost,
        LLMHostApiReportTotals,
    )

    hosts = []
    by_status: dict[str, int] = {}
    by_engine: dict[str, int] = {}
    gpus = 0
    cost_per_hour = Decimal("0")
    estimated_cost = Decimal("0")
    for llmhost in llmhosts:
        by_status[llmhost.status] = by_status.get(llmhost.status, 0) + 1
        by_engine[llmhost.inference_engine] = by_engine.get(llmhost.inference_engine, 0) + 1
        deployed = llmhost.is_deployed
        host_gpus = llmhost.gpu_count * llmhost.replicas if deployed else 0
        gpus += host_gpus
        # cost_per_hour is per replica.
        host_cost_per_hour = llmhost.cost_per_hour * llmhost.replicas if llmhost.cost_per_hour is not None else None
        if deployed and host_cost_per_hour is not None:
            cost_per_hour += host_cost_per_hour
        cost = llmhost.estimated_cost
        if cost is not None:
            estimated_cost += cost
        hosts.append(
            LLMHostApiReportHost(
                name=llmhost.name,
                owner=llmhost.user_profile.user.username,
                status=llmhost.status,
                engine=llmhost.inference_engine,
                model=llmhost.model_repository,
                task=llmhost.model_task,
                replicas=llmhost.replicas,
                ready_replicas=llmhost.ready_replicas,
                compute=compute.name if (compute := getattr(llmhost, "compute", None)) else None,
                gpus=host_gpus,
                gpu_type=llmhost.gpu_type or None,
                endpoint=llmhost.endpoint_url or None,
                public_url=llmhost.public_url or None,
                deployed_at=llmhost.deployed_at,
                uptime_hours=llmhost.uptime_hours,
                cost_per_hour=str(host_cost_per_hour) if host_cost_per_hour is not None else None,
                estimated_cost=str(cost) if cost is not None else None,
            )
        )
    deployed_states = Status.deployed()
    report = LLMHostApiReport(
        totals=LLMHostApiReportTotals(
            llmhosts=len(hosts),
            deployed=sum(count for status, count in by_status.items() if status in deployed_states),
            active=by_status.get(Status.ACTIVE.value, 0),
            errors=by_status.get(Status.ERROR.value, 0),
            gpus=gpus,
            cost_per_hour=str(cost_per_hour),
            estimated_cost=str(estimated_cost),
        ),
        by_status=by_status,
        by_engine=by_engine,
        llmhosts=hosts,
    )
    return report.model_dump(mode="json")


__all__ = ["HealthProber", "LLMHostObservation", "build_report", "in_cluster", "interpret", "summarize_pod"]
