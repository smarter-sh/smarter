"""
Render an LLMHost's Kubernetes resources.

:func:`render_resources` is a pure function of a :class:`RenderContext`: it calls neither
the database nor the cluster, so that what an LLMHost will create can be previewed, e.g.
with :meth:`~smarter.apps.llmhost.services.service.LLMHostService.plan`, and tested.

An LLMHost named ``llama`` with id 12 becomes, in the environment's namespace:

- ``PersistentVolumeClaim/llmhost-12-llama-models``: the model volume, at /models. Its
  PersistentVolume is provisioned by the storage class. Not created with ``storage.existingClaim``.
- ``Secret/llmhost-12-llama``: the Hugging Face token and the API key, if any.
- ``Deployment/llmhost-12-llama``: the inference server's pods.
- ``Service/llmhost-12-llama``: port 80, inside the cluster.
- ``Ingress/llmhost-12-llama``: with ``network.ingress``, HTTPS with a cert-manager certificate.

Every resource is labeled ``smarter.sh/llmhost=llmhost-12-llama``, which is how they are
observed and destroyed. The pods are also labeled ``smarter.sh/compute=<compute>``, and are
scheduled only on the nodes of their compute's node group, by its label and taint.
"""

import math
import re
from dataclasses import dataclass
from typing import Any, Optional

from smarter.apps.llmhost.const import (
    DEFAULT_CPU,
    DEFAULT_MEMORY,
    LABEL_ACCOUNT,
    LABEL_COMPUTE,
    LABEL_LLMHOST,
    MAX_RESOURCE_NAME_LENGTH,
    MODELS_MOUNT_PATH,
    RESOURCE_PREFIX,
    SERVICE_PORT,
    SHM_MOUNT_PATH,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostStorageAccessMode
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostSpec

from .engines import Engine, get_engine
from .sources import MODELS_VOLUME, ResolvedModel, resolve_model

SECRET_HF_TOKEN = "HF_TOKEN"
SECRET_API_KEY = "API_KEY"
CONTAINER_NAME = "engine"


def dns_label(value: str) -> str:
    """Return ``value`` as a DNS-1123 label: lower case alphanumerics and dashes."""
    label = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", label)


def resource_name(llmhost_id: int, name: str) -> str:
    """The base name of an LLMHost's Kubernetes resources, e.g. llmhost-12-llama-3-1-8b."""
    return f"{RESOURCE_PREFIX}-{llmhost_id}-{dns_label(name)}"[:MAX_RESOURCE_NAME_LENGTH].rstrip("-")


def label_selector(base_name: str) -> str:
    """The label selector of an LLMHost's Kubernetes resources."""
    return f"{LABEL_LLMHOST}={base_name}"


@dataclass(frozen=True)
class RenderContext:
    """
    Everything needed to render an LLMHost's Kubernetes resources.

    :param base_name: The base name of the resources, from :func:`resource_name`.
    :param namespace: The Kubernetes namespace.
    :param spec: The LLMHost's spec.
    :param served_name: The default model name that clients send, i.e. the LLMHost's name.
    :param account_number: The owner's account number, for labels.
    :param hostname: The Ingress hostname, if ``network.ingress``.
    :param cluster_issuer: The cert-manager ClusterIssuer of the Ingress' certificate.
    :param hf_token: Whether the Secret has a Hugging Face token.
    :param api_key: Whether the Secret has an API key.
    :param platform_name: For the app.kubernetes.io/part-of label.
    :param compute: The name of the LLMHost's compute, whose nodes the pods are scheduled on.
    :param compute_taint: The taint of the compute's nodes, which the pods tolerate.
    """

    base_name: str
    namespace: str
    spec: SAMLLMHostSpec
    served_name: str
    account_number: str
    hostname: Optional[str] = None
    cluster_issuer: Optional[str] = None
    hf_token: bool = False
    api_key: bool = False
    platform_name: str = "smarter"
    compute: Optional[str] = None
    compute_taint: Optional[dict[str, str]] = None

    @property
    def engine(self) -> Engine:
        return get_engine(self.spec.engine.name)

    @property
    def model(self) -> ResolvedModel:
        return resolve_model(self.spec.model, self.base_name)

    @property
    def labels(self) -> dict[str, str]:
        return {
            "app.kubernetes.io/name": self.base_name,
            "app.kubernetes.io/component": "llmhost",
            "app.kubernetes.io/managed-by": self.platform_name,
            LABEL_LLMHOST: self.base_name,
            LABEL_ACCOUNT: self.account_number,
        }

    @property
    def pod_labels(self) -> dict[str, str]:
        if not self.compute:
            return self.labels
        return {**self.labels, LABEL_COMPUTE: self.compute}

    @property
    def selector_labels(self) -> dict[str, str]:
        return {LABEL_LLMHOST: self.base_name}

    @property
    def volume_claim_name(self) -> str:
        return self.spec.storage.existingClaim or f"{self.base_name}-models"

    @property
    def secret_name(self) -> str:
        return self.base_name

    @property
    def tls_secret_name(self) -> str:
        return f"{self.base_name}-tls"

    @property
    def has_secret(self) -> bool:
        return self.hf_token or self.api_key

    @property
    def endpoint(self) -> str:
        """The base URL of the engine's API inside the cluster."""
        return f"http://{self.base_name}.{self.namespace}.svc.cluster.local{self.engine.openai_path}"

    @property
    def health_check_url(self) -> str:
        return f"http://{self.base_name}.{self.namespace}.svc.cluster.local{self.engine.health_path_for(self.spec)}"

    @property
    def public_url(self) -> Optional[str]:
        """The base URL of the engine's API at the Ingress, if any."""
        if not self.spec.network.ingress or not self.hostname:
            return None
        return f"https://{self.hostname}{self.engine.openai_path}"

    def metadata(self, name: Optional[str] = None, annotations: Optional[dict] = None) -> dict[str, Any]:
        retval: dict[str, Any] = {"name": name or self.base_name, "namespace": self.namespace, "labels": self.labels}
        if annotations:
            retval["annotations"] = annotations
        return retval


def render_volume_claim(ctx: RenderContext) -> Optional[dict[str, Any]]:
    """The model volume.

    None with storage.existingClaim, which is mounted instead.
    """
    storage = ctx.spec.storage
    if storage.existingClaim:
        return None
    spec: dict[str, Any] = {
        "accessModes": [storage.accessMode],
        "resources": {"requests": {"storage": storage.size}},
    }
    if storage.storageClass:
        spec["storageClassName"] = storage.storageClass
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": ctx.metadata(ctx.volume_claim_name),
        "spec": spec,
    }


def render_secret(ctx: RenderContext, hf_token: Optional[str], api_key: Optional[str]) -> Optional[dict[str, Any]]:
    """The Secret with the Hugging Face token and the API key.

    None if there are neither.
    """
    data = {}
    if hf_token:
        data[SECRET_HF_TOKEN] = hf_token
    if api_key:
        data[SECRET_API_KEY] = api_key
    if not data:
        return None
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "type": "Opaque",
        "metadata": ctx.metadata(ctx.secret_name),
        "stringData": data,
    }


def secret_env(ctx: RenderContext, variable: str, key: str) -> dict[str, Any]:
    return {"name": variable, "valueFrom": {"secretKeyRef": {"name": ctx.secret_name, "key": key}}}


def render_container(ctx: RenderContext) -> dict[str, Any]:
    """The inference server's container."""
    spec = ctx.spec
    engine = ctx.engine
    model = ctx.model
    served_name = engine.served_name(spec, ctx.served_name)
    api_key = ctx.api_key and engine.supports_api_key()

    env: list[dict[str, Any]] = [{"name": k, "value": v} for k, v in engine.env(spec, model).items()]
    if ctx.hf_token:
        env.append(secret_env(ctx, "HF_TOKEN", SECRET_HF_TOKEN))
        env.append(secret_env(ctx, "HUGGING_FACE_HUB_TOKEN", SECRET_HF_TOKEN))
    if api_key and engine.api_key_env:
        env.append(secret_env(ctx, engine.api_key_env, SECRET_API_KEY))

    resources = spec.resources
    memory = resources.memory or DEFAULT_MEMORY
    limits: dict[str, Any] = {"memory": memory}
    requests: dict[str, Any] = {"cpu": resources.cpu or DEFAULT_CPU, "memory": memory}
    if resources.gpuCount:
        limits[resources.gpuResource] = resources.gpuCount
        requests[resources.gpuResource] = resources.gpuCount

    period = spec.healthCheck.periodSeconds
    probe = engine.probe(spec)
    liveness_probe = {"httpGet": {"path": engine.health_path_for(spec), "port": "http"}}
    container: dict[str, Any] = {
        "name": CONTAINER_NAME,
        "image": engine.image(spec),
        "imagePullPolicy": "IfNotPresent",
        "args": engine.args(spec, model, served_name, api_key),
        "env": env,
        "ports": [{"name": "http", "containerPort": engine.container_port(spec), "protocol": "TCP"}],
        "resources": {"requests": requests, "limits": limits},
        "volumeMounts": [
            {"name": MODELS_VOLUME, "mountPath": MODELS_MOUNT_PATH},
            {"name": "dshm", "mountPath": SHM_MOUNT_PATH},
        ],
        # the startup probe allows time to download and load the weights.
        "startupProbe": {
            **probe,
            "periodSeconds": period,
            "timeoutSeconds": 10,
            "failureThreshold": math.ceil(spec.healthCheck.startupTimeoutSeconds / period),
        },
        "readinessProbe": {**probe, "periodSeconds": period, "timeoutSeconds": 10, "failureThreshold": 3},
        # a busy server may answer its health check slowly, so the liveness probe is lenient.
        "livenessProbe": {**liveness_probe, "periodSeconds": 30, "timeoutSeconds": 15, "failureThreshold": 5},
    }
    command = engine.command(spec, model)
    if command is not None:
        container["command"] = command
    return container


def render_deployment(ctx: RenderContext) -> dict[str, Any]:
    """The Deployment of the inference server, which restarts and reschedules its pods."""
    spec = ctx.spec
    resources = spec.resources
    node_selector = dict(resources.nodeSelector)
    if ctx.compute:
        node_selector[LABEL_COMPUTE] = ctx.compute
    tolerations = list(resources.tolerations)
    if resources.gpuCount and not any(t.get("key") == resources.gpuResource for t in tolerations):
        tolerations.append({"key": resources.gpuResource, "operator": "Exists", "effect": "NoSchedule"})
    if ctx.compute_taint and not any(t.get("key") == ctx.compute_taint["key"] for t in tolerations):
        tolerations.append(
            {"key": ctx.compute_taint["key"], "operator": "Exists", "effect": ctx.compute_taint["effect"]}
        )

    pod_spec: dict[str, Any] = {
        # writable model volume for non-root download containers; chown only once.
        "securityContext": {"fsGroup": 1000, "fsGroupChangePolicy": "OnRootMismatch"},
        "terminationGracePeriodSeconds": 60,
        "containers": [render_container(ctx)],
        "volumes": [
            {"name": MODELS_VOLUME, "persistentVolumeClaim": {"claimName": ctx.volume_claim_name}},
            {"name": "dshm", "emptyDir": {"medium": "Memory", "sizeLimit": resources.shmSize}},
        ],
    }
    init_containers = ctx.model.init_containers
    if init_containers:
        pod_spec["initContainers"] = init_containers
    if node_selector:
        pod_spec["nodeSelector"] = node_selector
    if tolerations:
        pod_spec["tolerations"] = tolerations
    if resources.serviceAccountName:
        pod_spec["serviceAccountName"] = resources.serviceAccountName

    single_writer = spec.storage.accessMode == SAMLLMHostStorageAccessMode.READ_WRITE_ONCE.value
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": ctx.metadata(),
        "spec": {
            "replicas": spec.scaling.replicas,
            # a ReadWriteOnce volume cannot be mounted by the old and new pods at once.
            "strategy": {"type": "Recreate"} if single_writer else {"type": "RollingUpdate"},
            "progressDeadlineSeconds": spec.healthCheck.startupTimeoutSeconds + 600,
            "selector": {"matchLabels": ctx.selector_labels},
            "template": {"metadata": {"labels": ctx.pod_labels}, "spec": pod_spec},
        },
    }


def render_service(ctx: RenderContext) -> dict[str, Any]:
    """The Service, which reaches the ready pods inside the cluster, on port 80."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": ctx.metadata(),
        "spec": {
            "type": "ClusterIP",
            "selector": ctx.selector_labels,
            "ports": [{"name": "http", "port": SERVICE_PORT, "targetPort": "http", "protocol": "TCP"}],
        },
    }


def render_ingress(ctx: RenderContext) -> Optional[dict[str, Any]]:
    """The Ingress, with a cert-manager certificate, if network.ingress.

    Mirrors the LLMClient Ingress.
    """
    if not ctx.spec.network.ingress or not ctx.hostname:
        return None
    annotations = {
        "kubernetes.io/tls-acme": "true",
        "traefik.ingress.kubernetes.io/router.entrypoints": "websecure",
        "traefik.ingress.kubernetes.io/router.middlewares": f"{ctx.namespace}-https-redirect@kubernetescrd",
    }
    if ctx.cluster_issuer:
        annotations["cert-manager.io/cluster-issuer"] = ctx.cluster_issuer
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": ctx.metadata(annotations=annotations),
        "spec": {
            "ingressClassName": "traefik",
            "rules": [
                {
                    "host": ctx.hostname,
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {"service": {"name": ctx.base_name, "port": {"number": SERVICE_PORT}}},
                            }
                        ]
                    },
                }
            ],
            "tls": [{"hosts": [ctx.hostname], "secretName": ctx.tls_secret_name}],
        },
    }


def render_resources(
    ctx: RenderContext, hf_token: Optional[str] = None, api_key: Optional[str] = None
) -> list[dict[str, Any]]:
    """
    Render an LLMHost's Kubernetes resources, in the order in which they are applied.

    :param ctx: The render context.
    :param hf_token: The Hugging Face token. Pass None to render a preview without secrets.
    :param api_key: The API key. Pass None to render a preview without secrets.
    """
    resources = [
        render_volume_claim(ctx),
        render_secret(ctx, hf_token, api_key),
        render_deployment(ctx),
        render_service(ctx),
        render_ingress(ctx),
    ]
    return [resource for resource in resources if resource is not None]


__all__ = [
    "RenderContext",
    "dns_label",
    "label_selector",
    "render_resources",
    "resource_name",
]
