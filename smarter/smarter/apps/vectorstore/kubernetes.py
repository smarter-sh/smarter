"""
Self-hosted Qdrant on Kubernetes.

Each self-hosted vectorstore gets its own Qdrant server: a StatefulSet of one replica, with a
persistent volume for its data and snapshots, a ClusterIP Service, and a Secret with its API
key. They are applied, observed and deleted with
:class:`~smarter.apps.infrastructure.services.kubernetes.KubernetesService`, and labeled
``smarter.sh/vectorstore: <name>``, so that they can be selected together.

- :meth:`QdrantKubernetes.apply` creates or updates them.
- :meth:`QdrantKubernetes.stop` deletes all but the volume, so that the data survives.
- :meth:`QdrantKubernetes.destroy` deletes the volume too.

The Qdrant image is the unprivileged variant, which runs as a non-root user.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

import yaml

from smarter.apps.infrastructure.services import KubernetesService, infrastructure
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterException

from .manifest.models.vectorstore.const import (
    DEFAULT_CPU,
    DEFAULT_MEMORY,
    DEFAULT_QDRANT_IMAGE,
    DEFAULT_STORAGE,
)
from .models import VectorstoreMeta

LABEL = "smarter.sh/vectorstore"
HTTP_PORT = 6333
GRPC_PORT = 6334
STORAGE_PATH = "/qdrant/storage"
SNAPSHOTS_PATH = f"{STORAGE_PATH}/snapshots"
API_KEY_ENV = "QDRANT__SERVICE__API_KEY"
UNPRIVILEGED_UID = 1000
STOP_KINDS = ["statefulset", "service", "secret"]
DESTROY_KINDS = STOP_KINDS + ["persistentvolumeclaim"]

_kubernetes_factory: Optional[Callable[[], KubernetesService]] = None


class VectorstoreKubernetesError(SmarterException):
    """The Kubernetes cluster is unavailable, or rejected a self-hosted vectorstore's resources."""


def configure_kubernetes(factory: Optional[Callable[[], Any]]) -> None:
    """Use another Kubernetes service, e.g. a fake in tests.

    None restores the default.
    """
    global _kubernetes_factory  # pylint: disable=global-statement
    _kubernetes_factory = factory


def get_kubernetes() -> KubernetesService:
    return _kubernetes_factory() if _kubernetes_factory else infrastructure.kubernetes


def unprivileged(image: str) -> str:
    """The unprivileged variant of a qdrant/qdrant image, which runs as a non-root user."""
    if image.startswith("qdrant/qdrant:") and not image.endswith("-unprivileged") and "@" not in image:
        return f"{image}-unprivileged"
    return image


@dataclass
class QdrantObservation:
    """The state of a self-hosted Qdrant server."""

    exists: bool
    ready: bool
    message: str


class QdrantKubernetes:
    """The Kubernetes resources of a self-hosted Qdrant server."""

    def __init__(self, vectorstore: VectorstoreMeta, kubernetes: Optional[KubernetesService] = None):
        self.vectorstore = vectorstore
        self.kubernetes = kubernetes or get_kubernetes()
        self.name = vectorstore.kubernetes_name
        self.namespace = smarter_settings.environment_namespace
        self.selector = f"{LABEL}={self.name}"

    @property
    def endpoint(self) -> str:
        """The Qdrant server's URL, inside the cluster."""
        return f"http://{self.name}.{self.namespace}.svc.cluster.local:{HTTP_PORT}"

    @property
    def labels(self) -> dict[str, str]:
        return {
            LABEL: self.name,
            "app.kubernetes.io/name": "qdrant",
            "app.kubernetes.io/instance": self.name,
            "app.kubernetes.io/managed-by": "smarter",
        }

    def render(self, api_key: str) -> list[dict[str, Any]]:
        """The Secret, Service and StatefulSet of the Qdrant server."""
        config = (self.vectorstore.spec or {}).get("selfHosted") or {}
        metadata = {"name": self.name, "namespace": self.namespace, "labels": self.labels}
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": metadata,
            "type": "Opaque",
            "stringData": {"api-key": api_key},
        }
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": metadata,
            "spec": {
                "type": "ClusterIP",
                "selector": {LABEL: self.name},
                "ports": [
                    {"name": "http", "port": HTTP_PORT, "targetPort": "http"},
                    {"name": "grpc", "port": GRPC_PORT, "targetPort": "grpc"},
                ],
            },
        }
        volume_claim: dict[str, Any] = {
            "metadata": {"name": "storage", "labels": self.labels},
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": config.get("storage") or DEFAULT_STORAGE}},
            },
        }
        if config.get("storageClass"):
            volume_claim["spec"]["storageClassName"] = config["storageClass"]
        memory = config.get("memory") or DEFAULT_MEMORY
        container = {
            "name": "qdrant",
            "image": unprivileged(config.get("image") or DEFAULT_QDRANT_IMAGE),
            "ports": [
                {"name": "http", "containerPort": HTTP_PORT},
                {"name": "grpc", "containerPort": GRPC_PORT},
            ],
            "env": [
                {"name": API_KEY_ENV, "valueFrom": {"secretKeyRef": {"name": self.name, "key": "api-key"}}},
                {"name": "QDRANT__STORAGE__SNAPSHOTS_PATH", "value": SNAPSHOTS_PATH},
                {"name": "QDRANT__TELEMETRY_DISABLED", "value": "true"},
            ],
            "resources": {
                "requests": {"cpu": config.get("cpu") or DEFAULT_CPU, "memory": memory},
                "limits": {"memory": memory},
            },
            "readinessProbe": {"httpGet": {"path": "/readyz", "port": "http"}, "periodSeconds": 10},
            "livenessProbe": {
                "httpGet": {"path": "/livez", "port": "http"},
                "initialDelaySeconds": 30,
                "periodSeconds": 30,
            },
            "securityContext": {
                "runAsNonRoot": True,
                "runAsUser": UNPRIVILEGED_UID,
                "allowPrivilegeEscalation": False,
            },
            "volumeMounts": [{"name": "storage", "mountPath": STORAGE_PATH}],
        }
        statefulset = {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": metadata,
            "spec": {
                "serviceName": self.name,
                "replicas": 1,
                "selector": {"matchLabels": {LABEL: self.name}},
                "template": {
                    "metadata": {"labels": self.labels},
                    "spec": {
                        "securityContext": {"fsGroup": UNPRIVILEGED_UID},
                        "containers": [container],
                    },
                },
                "volumeClaimTemplates": [volume_claim],
            },
        }
        return [secret, service, statefulset]

    def _require_cluster(self) -> None:
        if not self.kubernetes.ready:
            raise VectorstoreKubernetesError("The Kubernetes cluster is not available.")

    def apply(self, api_key: str) -> None:
        """Create or update the Qdrant server's resources."""
        self._require_cluster()
        manifest = yaml.safe_dump_all(self.render(api_key), sort_keys=False)
        try:
            self.kubernetes.apply_manifest(manifest)
        except Exception as e:
            raise VectorstoreKubernetesError(f"Kubernetes rejected Vectorstore {self.vectorstore.name}: {e}") from e

    def observe(self) -> QdrantObservation:
        """Whether the Qdrant server exists, and is ready."""
        statefulset = self.kubernetes.get_resource("statefulset", self.name, self.namespace)
        if not statefulset:
            return QdrantObservation(exists=False, ready=False, message="The Qdrant server does not exist.")
        status = statefulset.get("status") or {}
        if (status.get("readyReplicas") or 0) >= 1:
            return QdrantObservation(exists=True, ready=True, message="The Qdrant server is ready.")
        for pod in self.kubernetes.list_resources("pods", self.namespace, self.selector):
            for container in (pod.get("status") or {}).get("containerStatuses") or []:
                waiting = (container.get("state") or {}).get("waiting") or {}
                if waiting.get("reason") in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                    return QdrantObservation(
                        exists=True, ready=False, message=f"{waiting['reason']}: {waiting.get('message', '')}".strip()
                    )
        return QdrantObservation(exists=True, ready=False, message="The Qdrant server is starting.")

    def stop(self) -> bool:
        """Delete the Qdrant server, but not its volume, so that its data survives."""
        self._require_cluster()
        return self.kubernetes.delete_resources(STOP_KINDS, self.namespace, self.selector)

    def destroy(self) -> bool:
        """Delete the Qdrant server and its volume.

        Its data is lost.
        """
        self._require_cluster()
        return self.kubernetes.delete_resources(DESTROY_KINDS, self.namespace, self.selector)

    def logs(self, tail: int = 200) -> Optional[str]:
        return self.kubernetes.get_pod_logs(self.namespace, self.selector, container="qdrant", tail=tail)


__all__ = [
    "QdrantKubernetes",
    "QdrantObservation",
    "VectorstoreKubernetesError",
    "configure_kubernetes",
    "get_kubernetes",
]
