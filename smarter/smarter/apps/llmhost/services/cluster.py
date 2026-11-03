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
from smarter.lib.typing import SmarterDictType

from .exceptions import LLMHostClusterError


class ClusterBackend(ABC):
    """The operations that the LLMHost service layer needs from a Kubernetes cluster."""

    namespace: str

    @property
    @abstractmethod
    def ready(self) -> bool:
        """Whether the cluster is reachable."""

    @abstractmethod
    def apply(self, resources: list[SmarterDictType]) -> None:
        """
        Create or update resources.

        :param resources: The Kubernetes resources, as dicts.
        :raises LLMHostClusterError: if the cluster is unavailable, or rejects them.
        """

    @abstractmethod
    def get(self, kind: str, name: str) -> Optional[SmarterDictType]:
        """
        Return a resource, or None if it does not exist.

        :param kind: The resource's kind, e.g. ``deployment``.
        :param name: The resource's name.
        :returns: The resource, as a dict, or None.
        """

    @abstractmethod
    def list_resources(self, kind: str, selector: str) -> list[SmarterDictType]:
        """
        Return the resources of a kind that match a label selector.

        :param kind: The resources' kind, e.g. ``pod``.
        :param selector: A label selector, e.g. ``app=foo,tier=bar``.
        :returns: The matching resources, as dicts.
        """

    @abstractmethod
    def delete(self, kinds: list[str], selector: str) -> bool:
        """
        Delete the resources of several kinds that match a label selector.

        Idempotent.

        :param kinds: The kinds to delete, e.g. ``["deployment", "service"]``.
        :param selector: A label selector, e.g. ``app=foo``.
        :returns: Whether the deletion succeeded.
        :raises LLMHostClusterError: if the cluster is unavailable.
        """

    @abstractmethod
    def delete_named(self, kind: str, name: str) -> bool:
        """
        Delete one resource by name, e.g. a TLS Secret that cert-manager created without labels.

        :param kind: The resource's kind.
        :param name: The resource's name.
        :returns: Whether a resource was deleted.
        """

    @abstractmethod
    def logs(self, selector: str, container: Optional[str] = None, tail: int = 200) -> Optional[str]:
        """
        Return the most recent log lines of the pods that match a label selector.

        :param selector: A label selector, e.g. ``app=foo``.
        :param container: The container whose logs to read. Defaults to the pod's default container.
        :param tail: The most lines to return.
        :returns: The log lines, or None if they cannot be read.
        """


class KubectlClusterBackend(ClusterBackend):
    """The platform's cluster, through its Kubernetes service, i.e. kubectl."""

    def __init__(self, namespace: Optional[str] = None, helper=None):
        self.namespace = namespace or smarter_settings.environment_namespace
        self.helper = helper or infrastructure.kubernetes

    @property
    def ready(self) -> bool:
        """Whether the Kubernetes service can reach the cluster."""
        return bool(self.helper.ready)

    def apply(self, resources: list[SmarterDictType]) -> None:
        """
        Apply the resources to the cluster, as one multi-document YAML manifest.

        :param resources: The Kubernetes resources, as dicts.
        :raises LLMHostClusterError: if the cluster is unavailable, or rejects them.
        """
        if not self.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        manifest = yaml.safe_dump_all(resources, sort_keys=False)
        try:
            self.helper.apply_manifest(manifest)
        except KubernetesServiceError as e:
            raise LLMHostClusterError(f"The Kubernetes cluster rejected the resources: {e}") from e

    def get(self, kind: str, name: str) -> Optional[SmarterDictType]:
        """
        Return a resource in the namespace, or None if it does not exist.

        :param kind: The resource's kind.
        :param name: The resource's name.
        :returns: The resource, or None.
        """
        return self.helper.get_resource(kind, name, self.namespace)

    def list_resources(self, kind: str, selector: str) -> list[SmarterDictType]:
        """
        Return the resources of a kind in the namespace that match a label selector.

        :param kind: The resources' kind.
        :param selector: A label selector.
        :returns: The matching resources.
        """
        return self.helper.list_resources(kind, self.namespace, selector)

    def delete(self, kinds: list[str], selector: str) -> bool:
        """
        Delete the resources of several kinds in the namespace that match a label selector.

        :param kinds: The kinds to delete.
        :param selector: A label selector.
        :returns: Whether the deletion succeeded.
        :raises LLMHostClusterError: if the cluster is unavailable.
        """
        if not self.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        return self.helper.delete_resources(kinds, self.namespace, selector)

    def delete_named(self, kind: str, name: str) -> bool:
        """
        Delete one Secret or Ingress in the namespace by name.

        :param kind: ``secret`` or ``ingress``.
        :param name: The resource's name.
        :returns: Whether it was deleted.
        :raises LLMHostClusterError: if ``kind`` is neither.
        """
        if kind == "secret":
            return self.helper.delete_secret(name, self.namespace)
        if kind == "ingress":
            return self.helper.delete_ingress(name, self.namespace)
        raise LLMHostClusterError(f"delete_named() does not support {kind}.")

    def logs(self, selector: str, container: Optional[str] = None, tail: int = 200) -> Optional[str]:
        """
        Return the most recent log lines of the pods in the namespace that match a label selector.

        :param selector: A label selector.
        :param container: The container whose logs to read. Optional.
        :param tail: The most lines to return.
        :returns: The log lines, or None.
        """
        return self.helper.get_pod_logs(self.namespace, selector, container=container, tail=tail)


def _kind(kind: str) -> str:
    """Normalize a kind, e.g. 'Deployment', 'deployments' and 'deployment' are the same."""
    kind = kind.lower()
    if kind.endswith("s") and not kind.endswith("ss"):
        return kind[:-1]
    return kind


def _matches(resource: SmarterDictType, selector: str) -> bool:
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
        self.resources: dict[tuple[str, str], SmarterDictType] = {}
        self.applied: list[list[SmarterDictType]] = []
        self.deleted: list[tuple[list[str], str]] = []
        self.pod_logs: str = ""
        self.fail_apply: Optional[str] = None

    @property
    def ready(self) -> bool:
        """Whether the simulated cluster is reachable.

        Tests set it to simulate an outage.
        """
        return self._ready

    @ready.setter
    def ready(self, value: bool) -> None:
        """
        Set whether the simulated cluster is reachable.

        :param value: Whether it is reachable.
        """
        self._ready = value

    def apply(self, resources: list[SmarterDictType]) -> None:
        """
        Store copies of the resources, keeping each one's previous status, and record the call in :attr:`applied`.

        :param resources: The Kubernetes resources, as dicts.
        :raises LLMHostClusterError: if the cluster is not ready, or :attr:`fail_apply` is set.
        """
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

    def get(self, kind: str, name: str) -> Optional[SmarterDictType]:
        """
        Return a copy of a stored resource, or None.

        :param kind: The resource's kind, in any form, e.g. ``Deployment`` or ``deployments``.
        :param name: The resource's name.
        :returns: The resource, or None.
        """
        return copy.deepcopy(self.resources.get((_kind(kind), name)))

    def list_resources(self, kind: str, selector: str) -> list[SmarterDictType]:
        """
        Return copies of the stored resources of a kind that match a label selector.

        :param kind: The resources' kind, in any form.
        :param selector: A label selector of ``key=value`` terms.
        :returns: The matching resources.
        """
        kind = _kind(kind)
        matches = []
        for (resource_kind, _), resource in self.resources.items():
            if resource_kind == kind and _matches(resource, selector):
                matches.append(copy.deepcopy(resource))
        return matches

    def delete(self, kinds: list[str], selector: str) -> bool:
        """
        Delete the stored resources of several kinds that match a label selector, and record the call in :attr:`deleted`.

        Deleting Deployments also deletes pods, as Kubernetes garbage collects them.

        :param kinds: The kinds to delete.
        :param selector: A label selector.
        :returns: True.
        :raises LLMHostClusterError: if the cluster is not ready.
        """
        if not self.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        self.deleted.append((list(kinds), selector))
        kinds = [_kind(k) for k in kinds]
        if "deployment" in kinds:
            # Kubernetes garbage collects a Deployment's pods.
            kinds.append("pod")
        keys_to_delete = []
        for key, resource in self.resources.items():
            if key[0] in kinds and _matches(resource, selector):
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.resources[key]
        return True

    def delete_named(self, kind: str, name: str) -> bool:
        """
        Delete one stored resource by name.

        :param kind: The resource's kind, in any form.
        :param name: The resource's name.
        :returns: Whether it existed.
        """
        return self.resources.pop((_kind(kind), name), None) is not None

    def logs(self, selector: str, container: Optional[str] = None, tail: int = 200) -> Optional[str]:
        """
        Return the last ``tail`` lines of :attr:`pod_logs`, whatever the selector and container.

        :param selector: Unused.
        :param container: Unused.
        :param tail: The most lines to return.
        :returns: The log lines, or None if the cluster is not ready.
        """
        if not self.ready:
            return None
        lines = self.pod_logs.splitlines()
        last_lines = lines[-tail:]
        return "\n".join(last_lines)

    # --- simulation ---------------------------------------------------------------

    def set_deployment_status(self, name: str, **status) -> None:
        """Set a Deployment's status, e.g. readyReplicas=1."""
        self.resources[("deployment", name)].setdefault("status", {}).update(status)

    def add_pod(
        self, name: str, labels: dict[str, str], status: SmarterDictType, node_name: Optional[str] = None
    ) -> None:
        """
        Add a pod with a status, e.g. {'phase': 'Running', 'containerStatuses': [...]}, scheduled on a node.

        :param name: The pod's name.
        :param labels: The pod's labels.
        :param status: The pod's status, as Kubernetes reports it.
        :param node_name: The node it is scheduled on. Optional.
        """
        spec = {"nodeName": node_name} if node_name else {}
        self.resources[("pod", name)] = {
            "kind": "Pod",
            "metadata": {"name": name, "labels": labels},
            "spec": spec,
            "status": status,
        }

    def add_node(self, name: str, labels: dict[str, str], ready: bool = True) -> None:
        """
        Add a Node, e.g. one of a node group's, which has joined the cluster.

        :param name: The node's name, also used in its AWS provider id.
        :param labels: The node's labels.
        :param ready: Whether its Ready condition is True.
        """
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
