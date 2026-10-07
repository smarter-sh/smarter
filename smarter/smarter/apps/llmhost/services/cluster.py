"""
The Kubernetes cluster that LLMHosts run on.

The service layer talks to the cluster only through :class:`ClusterBackend`, so that it can
be tested with :class:`InMemoryClusterBackend`, and so that another way of reaching a cluster,
e.g. the Kubernetes Python client, or another cluster per account, is a new backend rather than
a change to the service layer.

:class:`KubectlClusterBackend`, the default, uses the platform's Kubernetes service,
:class:`~smarter.apps.infrastructure.services.kubernetes.KubernetesService`, i.e. kubectl with
the cloud provider's kubeconfig, in the environment's namespace.
"""

import copy
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

import yaml

from smarter.apps.infrastructure.exceptions import KubernetesServiceError
from smarter.apps.infrastructure.services import infrastructure
from smarter.common.conf import smarter_settings

from .exceptions import LLMHostClusterError


class ClusterBackend(ABC):
    """The operations that the LLMHost service layer needs from a Kubernetes cluster."""

    namespace: str

    @property
    @abstractmethod
    def ready(self) -> bool:
        """Whether the cluster is reachable."""

    @abstractmethod
    def apply(self, resources: list[dict[str, Any]]) -> None:
        """Create or update resources.

        Raises LLMHostClusterError if the cluster rejects them.
        """

    @abstractmethod
    def get(self, kind: str, name: str) -> Optional[dict[str, Any]]:
        """Return a resource, or None if it does not exist."""

    @abstractmethod
    def list_resources(self, kind: str, selector: str) -> list[dict[str, Any]]:
        """Return the resources of a kind that match a label selector."""

    @abstractmethod
    def delete(self, kinds: list[str], selector: str) -> bool:
        """Delete the resources of several kinds that match a label selector.

        Idempotent.
        """

    @abstractmethod
    def delete_named(self, kind: str, name: str) -> bool:
        """Delete one resource by name, e.g. a TLS Secret that cert-manager created without labels."""

    @abstractmethod
    def logs(self, selector: str, container: Optional[str] = None, tail: int = 200) -> Optional[str]:
        """Return the most recent log lines of the pods that match a label selector."""


class KubectlClusterBackend(ClusterBackend):
    """The platform's cluster, through its Kubernetes service, i.e. kubectl."""

    def __init__(self, namespace: Optional[str] = None, helper=None):
        self.namespace = namespace or smarter_settings.environment_namespace
        self.helper = helper or infrastructure.kubernetes

    @property
    def ready(self) -> bool:
        return bool(self.helper.ready)

    def apply(self, resources: list[dict[str, Any]]) -> None:
        if not self.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        manifest = yaml.safe_dump_all(resources, sort_keys=False)
        try:
            self.helper.apply_manifest(manifest)
        except KubernetesServiceError as e:
            raise LLMHostClusterError(f"The Kubernetes cluster rejected the resources: {e}") from e

    def get(self, kind: str, name: str) -> Optional[dict[str, Any]]:
        return self.helper.get_resource(kind, name, self.namespace)

    def list_resources(self, kind: str, selector: str) -> list[dict[str, Any]]:
        return self.helper.list_resources(kind, self.namespace, selector)

    def delete(self, kinds: list[str], selector: str) -> bool:
        if not self.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        return self.helper.delete_resources(kinds, self.namespace, selector)

    def delete_named(self, kind: str, name: str) -> bool:
        if kind == "secret":
            return self.helper.delete_secret(name, self.namespace)
        if kind == "ingress":
            return self.helper.delete_ingress(name, self.namespace)
        raise LLMHostClusterError(f"delete_named() does not support {kind}.")

    def logs(self, selector: str, container: Optional[str] = None, tail: int = 200) -> Optional[str]:
        return self.helper.get_pod_logs(self.namespace, selector, container=container, tail=tail)


def _kind(kind: str) -> str:
    """Normalize a kind, e.g. 'Deployment', 'deployments' and 'deployment' are the same."""
    kind = kind.lower()
    return kind[:-1] if kind.endswith("s") and not kind.endswith("ss") else kind


def _matches(resource: dict[str, Any], selector: str) -> bool:
    labels = resource.get("metadata", {}).get("labels", {}) or {}
    for term in filter(None, selector.split(",")):
        key, _, value = term.partition("=")
        if labels.get(key) != value:
            return False
    return True


class InMemoryClusterBackend(ClusterBackend):
    """
    A cluster in memory, for tests and local development.

    Applied resources are stored by kind and name. ``pods`` can be added with
    :meth:`add_pod`, and Deployment status with :meth:`set_deployment_status`, to simulate
    what a real cluster reports.
    """

    def __init__(self, namespace: str = "smarter-platform-test", ready: bool = True):
        self.namespace = namespace
        self._ready = ready
        self.resources: dict[tuple[str, str], dict[str, Any]] = {}
        self.applied: list[list[dict[str, Any]]] = []
        self.deleted: list[tuple[list[str], str]] = []
        self.pod_logs: str = ""
        self.fail_apply: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self._ready

    @ready.setter
    def ready(self, value: bool) -> None:
        self._ready = value

    def apply(self, resources: list[dict[str, Any]]) -> None:
        if not self.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        if self.fail_apply:
            raise LLMHostClusterError(self.fail_apply)
        self.applied.append(copy.deepcopy(resources))
        for resource in resources:
            key = (_kind(resource["kind"]), resource["metadata"]["name"])
            previous = self.resources.get(key, {})
            stored = copy.deepcopy(resource)
            if "status" in previous:
                stored["status"] = previous["status"]
            self.resources[key] = stored

    def get(self, kind: str, name: str) -> Optional[dict[str, Any]]:
        return copy.deepcopy(self.resources.get((_kind(kind), name)))

    def list_resources(self, kind: str, selector: str) -> list[dict[str, Any]]:
        kind = _kind(kind)
        return [copy.deepcopy(r) for (k, _), r in self.resources.items() if k == kind and _matches(r, selector)]

    def delete(self, kinds: list[str], selector: str) -> bool:
        if not self.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        self.deleted.append((list(kinds), selector))
        kinds = [_kind(k) for k in kinds]
        if "deployment" in kinds:
            # Kubernetes garbage collects a Deployment's pods.
            kinds.append("pod")
        for key in [key for key, r in self.resources.items() if key[0] in kinds and _matches(r, selector)]:
            del self.resources[key]
        return True

    def delete_named(self, kind: str, name: str) -> bool:
        return self.resources.pop((_kind(kind), name), None) is not None

    def logs(self, selector: str, container: Optional[str] = None, tail: int = 200) -> Optional[str]:
        if not self.ready:
            return None
        return "\n".join(self.pod_logs.splitlines()[-tail:])

    # --- simulation ---------------------------------------------------------------

    def set_deployment_status(self, name: str, **status) -> None:
        """Set a Deployment's status, e.g. readyReplicas=1."""
        self.resources[("deployment", name)].setdefault("status", {}).update(status)

    def add_pod(
        self, name: str, labels: dict[str, str], status: dict[str, Any], node_name: Optional[str] = None
    ) -> None:
        """Add a pod with a status, e.g. {'phase': 'Running', 'containerStatuses': [...]}, scheduled on a node."""
        self.resources[("pod", name)] = {
            "kind": "Pod",
            "metadata": {"name": name, "labels": labels},
            "spec": {"nodeName": node_name} if node_name else {},
            "status": status,
        }

    def add_node(self, name: str, labels: dict[str, str], ready: bool = True) -> None:
        """Add a Node, e.g. one of a node group's, which has joined the cluster."""
        self.resources[("node", name)] = {
            "kind": "Node",
            "metadata": {"name": name, "labels": labels},
            "spec": {"providerID": f"aws:///us-east-1a/i-{name}"},
            "status": {"conditions": [{"type": "Ready", "status": "True" if ready else "False"}]},
        }


_cluster_factory: Optional[Callable[[], ClusterBackend]] = None


def configure_cluster(factory: Optional[Callable[[], ClusterBackend]]) -> None:
    """
    Set the factory of the cluster backend that :func:`get_cluster` returns.

    Pass None to restore the default, :class:`KubectlClusterBackend`. Tests use this to
    install an :class:`InMemoryClusterBackend`.
    """
    global _cluster_factory  # pylint: disable=global-statement
    _cluster_factory = factory


def get_cluster() -> ClusterBackend:
    """Return the cluster backend."""
    if _cluster_factory is not None:
        return _cluster_factory()
    return KubectlClusterBackend()


__all__ = [
    "ClusterBackend",
    "InMemoryClusterBackend",
    "KubectlClusterBackend",
    "configure_cluster",
    "get_cluster",
]
