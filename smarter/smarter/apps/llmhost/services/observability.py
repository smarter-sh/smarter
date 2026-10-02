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
from typing import Any, Iterable, Optional

import requests

from smarter.apps.llmhost.const import HEALTH_CHECK_TIMEOUT_SECONDS
from smarter.apps.llmhost.manifest.enum import SAMLLMHostStatusEnum

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
    pods: list[dict[str, Any]] = field(default_factory=list)
    checked_at: Optional[datetime.datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """The observation, in camelCase, for JSON responses."""
        data = asdict(self)
        return {
            "status": data["status"],
            "message": data["message"],
            "replicas": data["replicas"],
            "readyReplicas": data["ready_replicas"],
            "healthy": data["healthy"],
            "endpoint": data["endpoint"],
            "publicUrl": data["public_url"],
            "pods": data["pods"],
            "checkedAt": self.checked_at.isoformat() if self.checked_at else None,
        }


def summarize_pod(pod: dict[str, Any]) -> dict[str, Any]:
    """A pod's name, phase, readiness, restarts, and the reason it is not ready, if any."""
    status = pod.get("status", {}) or {}
    containers = status.get("containerStatuses", []) or []
    init_containers = status.get("initContainerStatuses", []) or []
    reason = None
    for container in [*init_containers, *containers]:
        waiting = (container.get("state", {}) or {}).get("waiting")
        if waiting and waiting.get("reason") not in (None, "PodInitializing", "ContainerCreating"):
            reason = f"{container.get('name')}: {waiting.get('reason')}: {waiting.get('message', '')}".strip(": ")
            break
        last = (container.get("lastState", {}) or {}).get("terminated")
        if last and last.get("reason") in ("OOMKilled", "Error"):
            reason = f"{container.get('name')}: last terminated: {last.get('reason')}"
    if reason is None:
        for condition in status.get("conditions", []) or []:
            if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
                reason = f"{condition.get('reason', 'Unschedulable')}: {condition.get('message', '')}".strip(": ")
    return {
        "name": pod.get("metadata", {}).get("name"),
        "phase": status.get("phase"),
        "ready": bool(containers) and all(c.get("ready") for c in containers),
        "restarts": sum(int(c.get("restartCount", 0) or 0) for c in containers),
        "downloading": any("running" in (c.get("state", {}) or {}) for c in init_containers),
        "reason": reason,
    }


def _has_error(pod: dict[str, Any]) -> Optional[str]:
    status = pod.get("status", {}) or {}
    for container in [*(status.get("initContainerStatuses") or []), *(status.get("containerStatuses") or [])]:
        waiting = (container.get("state", {}) or {}).get("waiting") or {}
        if waiting.get("reason") in ERROR_REASONS:
            return f"{container.get('name')}: {waiting.get('reason')}: {waiting.get('message', '')}".strip(": ")
    return None


def _unschedulable(pod: dict[str, Any]) -> Optional[str]:
    for condition in (pod.get("status", {}) or {}).get("conditions", []) or []:
        if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
            return f"{condition.get('reason', 'Unschedulable')}: {condition.get('message', '')}".strip(": ")
    return None


# pylint: disable=too-many-return-statements
def interpret(deployment: Optional[dict[str, Any]], pods: list[dict[str, Any]]) -> tuple[str, str, int, int]:
    """
    Map an LLMHost's Deployment and pods to its status.

    :returns: (status, message, desired replicas, ready replicas)
    """
    if not deployment:
        return Status.INACTIVE.value, "Not deployed.", 0, 0
    desired = int((deployment.get("spec", {}) or {}).get("replicas", 1) or 0)
    dstatus = deployment.get("status", {}) or {}
    ready = int(dstatus.get("readyReplicas", 0) or 0)

    for condition in dstatus.get("conditions", []) or []:
        if condition.get("type") == "Progressing" and condition.get("reason") == "ProgressDeadlineExceeded":
            if ready == 0:
                return Status.ERROR.value, condition.get("message", "Progress deadline exceeded."), desired, ready

    errors = [e for e in (_has_error(pod) for pod in pods) if e]
    if desired and ready >= desired:
        return Status.ACTIVE.value, f"{ready}/{desired} replicas ready.", desired, ready
    if ready > 0:
        detail = f" {errors[0]}" if errors else ""
        return Status.DEGRADED.value, f"{ready}/{desired} replicas ready.{detail}", desired, ready
    if errors:
        return Status.ERROR.value, errors[0], desired, ready
    if any(summarize_pod(pod)["downloading"] for pod in pods):
        return Status.DOWNLOADING.value, "Copying the model weights to the model volume.", desired, ready
    unschedulable = [u for u in (_unschedulable(pod) for pod in pods) if u]
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


def build_report(llmhosts: Iterable[Any]) -> dict[str, Any]:
    """
    Summarize LLMHosts: their count by status and engine, the GPUs they use, and their cost.

    :param llmhosts: LLMHost instances.
    """
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
            {
                "name": llmhost.name,
                "owner": llmhost.user_profile.user.username,
                "status": llmhost.status,
                "engine": llmhost.inference_engine,
                "model": llmhost.model_repository,
                "task": llmhost.model_task,
                "replicas": llmhost.replicas,
                "readyReplicas": llmhost.ready_replicas,
                "compute": compute.name if (compute := getattr(llmhost, "compute", None)) else None,
                "gpus": host_gpus,
                "gpuType": llmhost.gpu_type or None,
                "endpoint": llmhost.endpoint_url or None,
                "publicUrl": llmhost.public_url or None,
                "deployedAt": llmhost.deployed_at.isoformat() if llmhost.deployed_at else None,
                "uptimeHours": llmhost.uptime_hours,
                "costPerHour": str(host_cost_per_hour) if host_cost_per_hour is not None else None,
                "estimatedCost": str(cost) if cost is not None else None,
            }
        )
    deployed_states = Status.deployed()
    return {
        "totals": {
            "llmhosts": len(hosts),
            "deployed": sum(count for status, count in by_status.items() if status in deployed_states),
            "active": by_status.get(Status.ACTIVE.value, 0),
            "errors": by_status.get(Status.ERROR.value, 0),
            "gpus": gpus,
            "costPerHour": str(cost_per_hour),
            "estimatedCost": str(estimated_cost),
        },
        "byStatus": by_status,
        "byEngine": by_engine,
        "llmhosts": hosts,
    }


__all__ = ["HealthProber", "LLMHostObservation", "build_report", "in_cluster", "interpret", "summarize_pod"]
