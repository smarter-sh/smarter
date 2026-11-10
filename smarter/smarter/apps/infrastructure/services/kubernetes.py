"""
The Kubernetes service: resources in the platform's Kubernetes cluster.

Kubernetes does not depend on a cloud: only the cluster's credentials do. So
:class:`KubernetesService` is implemented once, by :class:`KubectlKubernetesService`, with
`kubectl <https://kubernetes.io/docs/reference/kubectl/>`__, and the cloud provider contributes
only the kubeconfig, with
:meth:`~smarter.apps.infrastructure.providers.base.CloudProvider.update_kubeconfig`, e.g.
``aws eks update-kubeconfig`` for AWS EKS.

The platform uses it through :data:`smarter.apps.infrastructure.services.infrastructure`
``.kubernetes``. Tests replace it with :func:`configure_kubernetes`.

.. code-block:: python

    from smarter.apps.infrastructure.services import infrastructure

    infrastructure.kubernetes.apply_manifest(manifest)
"""

import os
import subprocess
import time
from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Optional

import yaml

from smarter.common.conf import smarter_settings
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from ..const import BILLABLE_KUBERNETES_KINDS, InfrastructureServiceNames
from ..exceptions import InfrastructureConfigurationError, KubernetesServiceError
from ..signals import resource_applied
from .base import InfrastructureService, refuse_in_unit_tests

if TYPE_CHECKING:
    from ..providers.base import CloudProvider

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

RESOURCE_TYPE_PREFIX = "kubernetes"


def billable_resources(manifest: str) -> list[tuple[str, str]]:
    """
    Return the resources of a manifest that provision billable cloud resources.

    - a PersistentVolumeClaim provisions a block storage volume.
    - a StatefulSet's volumeClaimTemplates provision one volume per replica.
    - a Service of type LoadBalancer provisions a cloud load balancer.

    :param manifest: A Kubernetes manifest, which may have several YAML documents.
    :returns: The (kind, name) of each, e.g. ``("persistentvolumeclaim", "data")``.
    """
    retval: list[tuple[str, str]] = []
    try:
        documents = [doc for doc in yaml.safe_load_all(manifest) if isinstance(doc, dict)]
    except yaml.YAMLError:
        return retval
    for doc in documents:
        kind = str(doc.get("kind", "")).lower()
        metadata = doc.get("metadata") or {}
        name = str(metadata.get("name", ""))
        spec = doc.get("spec") or {}
        if kind in BILLABLE_KUBERNETES_KINDS:
            retval.append((kind, name))
        elif kind == "statefulset" and spec.get("volumeClaimTemplates"):
            retval.append((kind, name))
        elif kind == "service" and spec.get("type") == "LoadBalancer":
            retval.append((kind, name))
    return retval


def redacted_manifest(manifest: str) -> str:
    """
    Return a manifest that can be logged: the values of its Secrets replaced with ``<redacted>``.

    A Secret's ``data`` and ``stringData`` hold credentials, e.g. an LLMHost's provider API key,
    in plain text or base64.

    :param manifest: A Kubernetes manifest, which may have several YAML documents.
    :returns: The manifest, with each Secret value redacted, or a placeholder if it isn't valid YAML.
    """
    try:
        documents = list(yaml.safe_load_all(manifest))
    except yaml.YAMLError:
        return "<a manifest that is not valid YAML, not logged>"
    for doc in documents:
        if isinstance(doc, dict) and str(doc.get("kind", "")).lower() == "secret":
            for field in ("data", "stringData"):
                if isinstance(doc.get(field), dict):
                    doc[field] = {key: "<redacted>" for key in doc[field]}
    return yaml.safe_dump_all(documents, sort_keys=False)


def manifest_kinds(manifest: str) -> list[str]:
    """Return the kinds of a manifest's resources, e.g. ``["Ingress"]``."""
    try:
        return [str(doc.get("kind")) for doc in yaml.safe_load_all(manifest) if isinstance(doc, dict)]
    except yaml.YAMLError:
        return []


class KubernetesService(InfrastructureService):
    """
    The platform's Kubernetes cluster.

    Implementations provide the primitives: :meth:`apply_manifest`, :meth:`get_resource`,
    :meth:`list_resources`, :meth:`delete_resource`, :meth:`delete_resources` and
    :meth:`get_pod_logs`, and optionally :meth:`find_resources`, for the inventory. The ingress
    operations that LLMClient deployments use are built on them.
    """

    service_name = InfrastructureServiceNames.KUBERNETES
    error_class = KubernetesServiceError

    certificate_wait_seconds: float = 60
    """Seconds between the checks of a cert-manager certificate, in :meth:`verify_ingress_resources`."""

    # --------------------------------------------------------------------------
    # primitives
    # --------------------------------------------------------------------------
    @abstractmethod
    def apply_manifest(self, manifest: str) -> None:
        """
        Create or update the resources of a manifest.

        :raises KubernetesServiceError: If the cluster rejects them.
        """

    @abstractmethod
    def get_resource(self, kind: str, name: str, namespace: str) -> Optional[SmarterDictType]:
        """
        Return a resource, or None if it does not exist or the cluster is unavailable.

        :param kind: The kind, e.g. ``ingress``.
        :param name: The resource's name.
        :param namespace: The namespace.
        :returns: The resource, as ``kubectl get -o json`` returns it, or None.
        """

    def get_resources(self, resources: list[tuple[str, str]], namespace: str) -> dict[tuple[str, str], SmarterDictType]:
        """
        Return several resources at once.

        Implementations may override it to fetch them in one request. This one gets each in turn.

        :param resources: The (kind, name) of each resource, with a lowercase kind, e.g. ``("ingress", "app")``.
        :param namespace: The namespace.
        :returns: The resources that exist, keyed by their (kind, name).
        """
        retval: dict[tuple[str, str], SmarterDictType] = {}
        for kind, name in resources:
            resource = self.get_resource(kind, name, namespace)
            if resource is not None:
                retval[(kind, name)] = resource
        return retval

    @abstractmethod
    def list_resources(self, kind: str, namespace: str, selector: Optional[str] = None) -> list[SmarterDictType]:
        """
        Return the resources of a kind, optionally those that match a label selector.

        :param kind: The kind, e.g. ``pods``.
        :param namespace: The namespace.
        :param selector: A label selector, e.g. ``app=qdrant``, or None for all.
        :returns: The resources, or an empty list.
        """

    def find_resources(self, kind: str, namespace: Optional[str] = None) -> Optional[list[SmarterDictType]]:
        """
        Return every resource of a kind, for the inventory.

        Unlike :meth:`list_resources`, it tells a kind that has no resources from one that could
        not be listed, so that the inventory never mistakes an unavailable cluster for an empty one.
        This implementation cannot list, and returns None.

        :param kind: The kind, e.g. ``node``.
        :param namespace: The namespace of a namespaced kind, or None for a cluster-scoped kind,
            e.g. a node.
        :returns: The resources, or None if they could not be listed, e.g. because the cluster
            is unavailable, or the kind's CustomResourceDefinition is not installed.
        """
        return None

    @abstractmethod
    def delete_resource(self, kind: str, name: str, namespace: str) -> bool:
        """Delete a resource by name.

        A resource that does not exist counts as deleted.
        """

    @abstractmethod
    def delete_resources(self, kinds: list[str], namespace: str, selector: str) -> bool:
        """
        Delete the resources of several kinds that match a label selector.

        Idempotent. A selector is required, so that a namespace is never emptied by mistake.
        """

    @abstractmethod
    def get_pod_logs(
        self, namespace: str, selector: str, container: Optional[str] = None, tail: int = 200
    ) -> Optional[str]:
        """
        Return the most recent log lines of the pods that match a label selector.

        :param namespace: The namespace.
        :param selector: A label selector.
        :param container: The container, or None for the pod's default.
        :param tail: How many lines of each pod.
        :returns: The logs, or None if they could not be read.
        """

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    # --------------------------------------------------------------------------
    # resources
    # --------------------------------------------------------------------------
    def verify_ingress(self, name: str, namespace: str) -> bool:
        """
        Whether an Ingress exists.

        :param name: The Ingress's name.
        :param namespace: The Ingress's namespace.
        :returns: True if it exists.
        """
        return self.get_resource("ingress", name, namespace) is not None

    def verify_secret(self, name: str, namespace: str) -> bool:
        """
        Whether a Secret exists.

        :param name: The Secret's name.
        :param namespace: The Secret's namespace.
        :returns: True if it exists.
        """
        return self.get_resource("secret", name, namespace) is not None

    def verify_certificate(self, name: str, namespace: str) -> bool:
        """
        Whether a cert-manager Certificate exists, and is Ready, i.e. issued.

        :param name: The Certificate's name.
        :param namespace: The Certificate's namespace.
        """
        return self._certificate_ready(self.get_resource("certificate", name, namespace), name, namespace)

    def _certificate_ready(self, certificate: Optional[SmarterDictType], name: str, namespace: str) -> bool:
        """Whether a cert-manager Certificate exists, and its Ready condition is True."""
        if certificate is None:
            return False
        status = certificate.get("status") or {}
        conditions = status.get("conditions") or []
        ready = None
        for condition in conditions:
            if condition.get("type") == "Ready":
                ready = condition.get("status")
                break
        if str(ready).lower() == "true":
            logger.info("%s certificate %s %s is issued", self.formatted_class_name, namespace, name)
            return True
        logger.warning("%s certificate %s %s is not ready: %s", self.formatted_class_name, namespace, name, ready)
        return False

    def verify_ingress_resources(
        self, hostname: str, namespace: str, max_attempts: int = 30
    ) -> tuple[bool, bool, bool]:
        """
        Verify that a host's Ingress, its cert-manager Certificate, and its TLS Secret exist.

        The Ingress is named after the host, and the Certificate and Secret ``<host>-tls``.

        :param hostname: The host, e.g. ``example.3141-5926-5359.api.example.com``.
        :param namespace: The namespace.
        :param max_attempts: How many times to check the Certificate, a minute apart. A Celery
            task passes 1, and checks again later, so that it does not block its worker.
        :returns: Whether the Ingress, the Certificate, and the Secret are verified.
        """
        secret_name = f"{hostname}-tls"
        # one request for all three: each kubectl call also fetches a cluster token, which is slow.
        found = self.get_resources(
            [("ingress", hostname), ("certificate", secret_name), ("secret", secret_name)], namespace
        )
        ingress_verified = ("ingress", hostname) in found
        secret_verified = ("secret", secret_name) in found
        certificate_verified = self._certificate_ready(found.get(("certificate", secret_name)), secret_name, namespace)
        for _ in range(1, max(1, max_attempts)):
            if certificate_verified:
                break
            self._sleep(self.certificate_wait_seconds)
            certificate_verified = self.verify_certificate(secret_name, namespace)
        return ingress_verified, certificate_verified, secret_verified

    def delete_ingress(self, name: str, namespace: str) -> bool:
        """
        Delete an Ingress.

        :param name: The Ingress's name.
        :param namespace: The Ingress's namespace.
        :returns: True if it was deleted, or did not exist.
        """
        return self.delete_resource("ingress", name, namespace)

    def delete_certificate(self, name: str, namespace: str) -> bool:
        """
        Delete a cert-manager Certificate.

        :param name: The Certificate's name.
        :param namespace: The Certificate's namespace.
        :returns: True if it was deleted, or did not exist.
        """
        return self.delete_resource("certificate", name, namespace)

    def delete_secret(self, name: str, namespace: str) -> bool:
        """
        Delete a Secret.

        :param name: The Secret's name.
        :param namespace: The Secret's namespace.
        :returns: True if it was deleted, or did not exist.
        """
        return self.delete_resource("secret", name, namespace)

    def delete_ingress_resources(self, hostname: str, namespace: str) -> tuple[bool, bool, bool]:
        """
        Delete a host's Ingress, its cert-manager Certificate, and its TLS Secret.

        :returns: Whether the Ingress, the Certificate, and the Secret were deleted.
        """
        secret_name = f"{hostname}-tls"
        return (
            self.delete_ingress(hostname, namespace),
            self.delete_certificate(secret_name, namespace),
            self.delete_secret(secret_name, namespace),
        )


class KubectlKubernetesService(KubernetesService):
    """
    The platform's Kubernetes cluster, through kubectl.

    The cluster is ready once kubectl is configured, with the provider's
    :meth:`~smarter.apps.infrastructure.providers.base.CloudProvider.update_kubeconfig`, and the
    environment's namespace, ``smarter_settings.environment_namespace``, exists.

    :param provider: The cloud provider that writes the kubeconfig. None for a cluster whose
        kubeconfig is already in place.
    :param allow_in_tests: Allow kubectl in the unit tests, e.g. when subprocess is mocked.
    """

    def __init__(self, provider: Optional["CloudProvider"] = None, allow_in_tests: bool = False, **kwargs):
        super().__init__(provider_name=provider.provider_name if provider else "kubectl", **kwargs)
        self.provider = provider
        self.allow_in_tests = allow_in_tests
        self._configured = False
        self._namespace_verified = False
        self._kubeconfig: Optional[SmarterDictType] = None
        self._token: Optional[str] = None
        self._token_expires: float = 0.0

    # --------------------------------------------------------------------------
    # readiness
    # --------------------------------------------------------------------------
    @property
    def configured(self) -> bool:
        """Whether kubectl is configured for the cluster."""
        if not self._configured:
            if self.provider is None:
                self._configured = True
            else:
                try:
                    self._configured = self.provider.update_kubeconfig()
                except InfrastructureConfigurationError as e:
                    logger.debug("%s %s", self.formatted_class_name, e)
                    self._configured = False
        return self._configured

    @property
    def namespace_verified(self) -> bool:
        """Whether the environment's namespace exists."""
        if not self._namespace_verified:
            self._namespace_verified = self.verify_namespace(smarter_settings.environment_namespace)
        return self._namespace_verified

    @property
    def ready(self) -> bool:
        """
        Whether kubectl is configured for the cluster, and the environment's namespace exists.

        Records the connection state, which sends a signal when it changes.
        """
        if not self.configured:
            return self.connection_state(False, "kubectl is not configured for the cluster")
        if not self.namespace_verified:
            return self.connection_state(
                False, f"the namespace {smarter_settings.environment_namespace} does not exist"
            )
        return self.connection_state(True)

    @property
    def kubeconfig_path(self) -> str:
        """The path of the platform's kubeconfig file."""
        return os.path.join(smarter_settings.data_directory, ".kube", "config")

    @property
    def kubeconfig(self) -> SmarterDictType:
        """The platform's kubeconfig file."""
        if self._kubeconfig is None:
            self._kubeconfig = get_readonly_yaml_file(self.kubeconfig_path)
        return self._kubeconfig

    # --------------------------------------------------------------------------
    # kubectl
    # --------------------------------------------------------------------------
    def _bearer_token(self) -> Optional[str]:
        """
        Return the provider's bearer token for the cluster, which is reused until it expires.

        Without one, kubectl authenticates with its kubeconfig, which for EKS runs ``aws eks
        get-token`` on every call: a Python process that takes seconds to start on a busy worker.
        """
        if self.provider is None:
            return None
        if self._token is None or time.time() >= self._token_expires:
            result = self.provider.get_kubernetes_token()
            self._token, self._token_expires = result if result else (None, 0.0)
        return self._token

    def _kubectl(self, *args: str, stdin: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run kubectl, with the provider's bearer token, if it has one.

        :raises InfrastructureConfigurationError: In the unit tests, unless allowed.
        """
        refuse_in_unit_tests("the Kubernetes cluster", self.allow_in_tests)
        command = ["kubectl", *args]
        token = self._bearer_token()
        if token:
            # a request that has a token does not run the kubeconfig's exec command.
            command += ["--token", token]
        return subprocess.run(command, input=stdin, capture_output=True, text=True, check=False)  # nosec B603 B607

    def _kubectl_json(self, *args: str) -> Optional[SmarterDictType]:
        """Run kubectl with ``-o json``, and return its output, or None if it fails or is empty."""
        result = self._kubectl(*args, "-o", "json")
        if result.returncode != 0:
            logger.warning("%s kubectl %s failed: %s", self.formatted_class_name, " ".join(args), result.stderr)
            return None
        if not result.stdout.strip():
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error("%s kubectl %s returned invalid json: %s", self.formatted_class_name, " ".join(args), e)
            return None

    def verify_namespace(self, namespace: str) -> bool:
        """Whether a namespace exists."""
        if not self.configured:
            return False
        try:
            return self._kubectl_json("get", "namespace", namespace) is not None
        except InfrastructureConfigurationError as e:
            logger.debug("%s %s", self.formatted_class_name, e)
            return False

    def apply_manifest(self, manifest: str) -> None:
        """
        Create or update the resources of a manifest, with ``kubectl apply``.

        Resources that provision billable cloud resources, see :func:`billable_resources`, are
        announced with the billable resource signals. Nothing is applied if the cluster is not
        ready.

        :param manifest: The manifest, which may have several YAML documents.
        :raises KubernetesServiceError: If the cluster rejects it.
        """
        logger.info(
            "%s.apply_manifest() applying a manifest to the cluster:\n%s",
            self.formatted_class_name,
            redacted_manifest(manifest),
        )
        if not self.ready:
            logger.error("%s the cluster is not ready. The manifest was not applied.", self.formatted_class_name)
            return None
        billable = [
            self.creating_resource(f"{RESOURCE_TYPE_PREFIX}.{kind}", name, billable=True)
            for kind, name in billable_resources(manifest)
        ]
        with self.operation("apply_manifest"):
            result = self._kubectl("apply", "-f", "-", stdin=manifest)
            if result.returncode != 0:
                raise KubernetesServiceError(f"Failed to apply manifest: {result.stderr}")
        for resource in billable:
            self.created_resource(resource, resource_id=resource["resource_name"])
        self.send(resource_applied, kinds=manifest_kinds(manifest))
        return None

    def get_resource(self, kind: str, name: str, namespace: str) -> Optional[SmarterDictType]:
        """
        Return a resource with ``kubectl get``.

        :param kind: The kind, e.g. ``ingress``.
        :param name: The resource's name.
        :param namespace: The namespace.
        :returns: The resource, or None if it does not exist, kubectl fails, or the cluster is not ready.
        """
        if not self.ready:
            return None
        return self._kubectl_json("get", kind, name, "-n", namespace, "--ignore-not-found")

    def get_resources(self, resources: list[tuple[str, str]], namespace: str) -> dict[tuple[str, str], SmarterDictType]:
        """
        Return several resources with one ``kubectl get``.

        Each kubectl call fetches a cluster token, e.g. with ``aws eks get-token``, which takes
        seconds, so one call rather than several frees a Celery worker sooner. If the call fails,
        e.g. because a kind's CustomResourceDefinition is not installed, each resource is fetched
        in turn.
        """
        if not resources or not self.ready:
            return {}
        refs = [f"{kind}/{name}" for kind, name in resources]
        result = self._kubectl("get", *refs, "-n", namespace, "--ignore-not-found", "-o", "json")
        if result.returncode != 0:
            logger.warning("%s kubectl get %s failed: %s", self.formatted_class_name, " ".join(refs), result.stderr)
            return super().get_resources(resources, namespace)
        if not result.stdout.strip():
            return {}
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error("%s kubectl get %s returned invalid json: %s", self.formatted_class_name, " ".join(refs), e)
            return {}
        # kubectl returns a List of several resources, or the resource itself when only one exists.
        if output.get("kind") == "List":
            items = output.get("items", [])
        else:
            items = [output]
        found: dict[tuple[str, str], SmarterDictType] = {}
        for item in items:
            item_kind = str(item.get("kind", "")).lower()
            metadata = item.get("metadata") or {}
            item_name = str(metadata.get("name", ""))
            found[(item_kind, item_name)] = item
        retval = {resource: found[resource] for resource in resources if resource in found}
        return retval

    def list_resources(self, kind: str, namespace: str, selector: Optional[str] = None) -> list[SmarterDictType]:
        """
        Return the resources of a kind with ``kubectl get``, optionally those that match a label selector.

        :param kind: The kind, e.g. ``pods``.
        :param namespace: The namespace.
        :param selector: A label selector, e.g. ``app=qdrant``, or None for all.
        :returns: The resources, or an empty list if there are none, kubectl fails, or the cluster is not ready.
        """
        if not self.ready:
            return []
        args = ["get", kind, "-n", namespace]
        if selector:
            args += ["-l", selector]
        output = self._kubectl_json(*args)
        return (output or {}).get("items", [])

    def find_resources(self, kind: str, namespace: Optional[str] = None) -> Optional[list[SmarterDictType]]:
        """
        Return every resource of a kind with ``kubectl get``, for the inventory.

        :param kind: The kind, e.g. ``node``.
        :param namespace: The namespace of a namespaced kind, or None for a cluster-scoped kind.
        :returns: The resources, or None if they could not be listed, e.g. because kubectl failed, its
            output is not a list, or the cluster is not ready.
        """
        if not self.ready:
            return None
        args = ["get", kind] + (["-n", namespace] if namespace else [])
        result = self._kubectl(*args, "-o", "json")
        if result.returncode != 0:
            logger.warning("%s kubectl %s failed: %s", self.formatted_class_name, " ".join(args), result.stderr)
            return None
        try:
            items = json.loads(result.stdout).get("items")
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error("%s kubectl %s returned invalid json: %s", self.formatted_class_name, " ".join(args), e)
            return None
        return items if isinstance(items, list) else None

    def delete_resource(self, kind: str, name: str, namespace: str) -> bool:
        """
        Delete a resource with ``kubectl delete``.

        A resource that does not exist counts as deleted.

        Sends the destroying and destroyed resource signals, which record it in the ledger, billable if
        its kind is in ``BILLABLE_KUBERNETES_KINDS``.

        :param kind: The kind, e.g. ``ingress``.
        :param name: The resource's name.
        :param namespace: The namespace.
        :returns: True if it was deleted, False if kubectl failed or the cluster is not ready.
        """
        if not self.ready:
            return False
        billable = kind.lower() in BILLABLE_KUBERNETES_KINDS
        resource = self.destroying_resource(f"{RESOURCE_TYPE_PREFIX}.{kind.lower()}", name, name, billable=billable)
        # --ignore-not-found: a resource that is already gone counts as deleted.
        result = self._kubectl("delete", kind, name, "-n", namespace, "--ignore-not-found")
        if result.returncode != 0:
            logger.error("%s failed to delete %s %s: %s", self.formatted_class_name, kind, name, result.stderr)
            return False
        self.destroyed_resource(resource)
        return True

    def delete_resources(self, kinds: list[str], namespace: str, selector: str) -> bool:
        """
        Delete the resources of several kinds that match a label selector, with one ``kubectl delete``.

        Sends the destroying and destroyed resource signals for each billable kind.

        :param kinds: The kinds, e.g. ``["statefulset", "service"]``.
        :param namespace: The namespace.
        :param selector: A label selector, which is required, so that a namespace is never emptied by mistake.
        :returns: True if they were deleted, False if kubectl failed or the cluster is not ready.
        :raises KubernetesServiceError: If ``kinds`` or ``selector`` is empty.
        """
        if not kinds or not selector:
            raise KubernetesServiceError("delete_resources() requires kinds and a label selector.")
        if not self.ready:
            return False
        billable = [
            self.destroying_resource(f"{RESOURCE_TYPE_PREFIX}.{kind.lower()}", selector, selector, billable=True)
            for kind in kinds
            if kind.lower() in BILLABLE_KUBERNETES_KINDS
        ]
        result = self._kubectl("delete", ",".join(kinds), "-n", namespace, "-l", selector, "--ignore-not-found")
        if result.returncode != 0:
            logger.error("%s failed to delete %s %s: %s", self.formatted_class_name, kinds, selector, result.stderr)
            return False
        for resource in billable:
            self.destroyed_resource(resource)
        return True

    def get_pod_logs(
        self, namespace: str, selector: str, container: Optional[str] = None, tail: int = 200
    ) -> Optional[str]:
        """
        Return the most recent log lines of the pods that match a label selector, with ``kubectl logs``.

        :param namespace: The namespace.
        :param selector: A label selector.
        :param container: The container, or None for the pod's default.
        :param tail: How many lines of each pod.
        :returns: The logs, each line prefixed with its pod. If kubectl fails, its output and error,
            which explain why, e.g. a pod that is still pulling its image. None if the cluster is not ready.
        """
        if not self.ready:
            return None
        args = ["logs", "-n", namespace, "-l", selector, "--tail", str(tail), "--prefix"]
        if container:
            args += ["-c", container]
        result = self._kubectl(*args)
        if result.returncode == 0:
            return result.stdout
        # the error explains why there are no logs, e.g. a pod that is still pulling its image.
        logger.warning("%s failed to get the logs of %s: %s", self.formatted_class_name, selector, result.stderr)
        return (result.stdout or "") + (result.stderr or "")


def matches_selector(item: SmarterDictType, selector: Optional[str]) -> bool:
    """
    Decide whether a resource's labels match a label selector, as ``kubectl get -l`` does.

    Only equality requirements are supported, e.g. ``app.kubernetes.io/name=smarter,tier=web``, which
    are all that the platform uses. Every requirement must match.

    :param item: The resource, as ``kubectl get -o json`` returns it.
    :param selector: The selector, or None or an empty string, which every resource matches.
    :returns: True if every requirement of the selector matches one of the resource's labels.
    """
    if not selector:
        return True
    metadata = item.get("metadata") or {}
    labels = metadata.get("labels") or {}
    for requirement in selector.split(","):
        key, _, value = requirement.strip().partition("=")
        if labels.get(key) != value:
            return False
    return True


class InMemoryKubernetesService(KubernetesService):
    """
    A Kubernetes cluster in memory, for tests and local development.

    Its resources are :attr:`items`: lists of resources, as ``kubectl get -o json`` returns them,
    keyed by kind, e.g. ``{"pod": [...], "node": [...]}``. A kind that is not a key cannot be
    listed: :meth:`find_resources` returns None for it, as for a cluster that is unavailable, or a
    CustomResourceDefinition that is not installed.

    :param ready: Whether the cluster is ready.
    :param provider_name: The provider's name, in signals and logs.
    """

    def __init__(self, ready: bool = True, provider_name: str = "memory", **kwargs):
        super().__init__(provider_name=provider_name, **kwargs)
        self._ready = ready
        self.items: dict[str, list[SmarterDictType]] = {}
        self.calls: list[tuple[str, Optional[str]]] = []
        """The (kind, namespace) of every :meth:`find_resources` and :meth:`list_resources` call, in order."""
        self.manifests: list[str] = []
        """Every manifest that :meth:`apply_manifest` received, in order."""

    @property
    def ready(self) -> bool:
        """Whether the cluster is ready, as set in the constructor."""
        return self._ready

    def _in(self, kind: str, namespace: Optional[str]) -> list[SmarterDictType]:
        """
        Return the resources of a kind in one namespace, or in every namespace.

        :param kind: The kind, e.g. ``pod``.
        :param namespace: The namespace, or None for every namespace, e.g. for a cluster-scoped kind
            such as ``node``.
        :returns: The resources, in the order of :attr:`items`.
        """
        found = []
        for item in self.items.get(kind, []):
            if namespace is None:
                found.append(item)
                continue
            metadata = item.get("metadata") or {}
            if metadata.get("namespace") == namespace:
                found.append(item)
        return found

    def apply_manifest(self, manifest: str) -> None:
        """
        Record a manifest in :attr:`manifests`, without creating its resources.

        :param manifest: The manifest.
        """
        self.manifests.append(manifest)

    def get_resource(self, kind: str, name: str, namespace: str) -> Optional[SmarterDictType]:
        """
        Find one resource of :attr:`items` by its kind, name and namespace.

        :param kind: The kind, e.g. ``ingress``.
        :param name: The resource's name.
        :param namespace: The resource's namespace.
        :returns: The resource, or None if there is none.
        """
        for item in self._in(kind, namespace):
            metadata = item.get("metadata") or {}
            if metadata.get("name") == name:
                return item
        return None

    def list_resources(self, kind: str, namespace: str, selector: Optional[str] = None) -> list[SmarterDictType]:
        """
        Return the resources of a kind in a namespace that match a label selector, and record the call.

        :param kind: The kind, e.g. ``pod``.
        :param namespace: The namespace.
        :param selector: An equality label selector, or None for every resource (see :func:`matches_selector`).
        :returns: The resources, or an empty list if the cluster is not ready, or has none.
        """
        self.calls.append((kind, namespace))
        if not self.ready:
            return []
        found = []
        for item in self._in(kind, namespace):
            if matches_selector(item, selector):
                found.append(item)
        return found

    def find_resources(self, kind: str, namespace: Optional[str] = None) -> Optional[list[SmarterDictType]]:
        """
        Return every resource of a kind, and record the call.

        :param kind: The kind, e.g. ``node``.
        :param namespace: The namespace of a namespaced kind, or None for every namespace.
        :returns: The resources, or None if the cluster is not ready, or the kind is not a key of
            :attr:`items`, as for a cluster that cannot be read.
        """
        self.calls.append((kind, namespace))
        if not self.ready:
            return None
        if kind not in self.items:
            return None
        return self._in(kind, namespace)

    def delete_resource(self, kind: str, name: str, namespace: str) -> bool:
        """
        Remove a resource from :attr:`items`.

        :param kind: The kind.
        :param name: The resource's name.
        :param namespace: The resource's namespace.
        :returns: True, also for a resource that does not exist, as Kubernetes' delete is idempotent.
        """
        item = self.get_resource(kind, name, namespace)
        if item is not None:
            self.items[kind].remove(item)
        return True

    def delete_resources(self, kinds: list[str], namespace: str, selector: str) -> bool:
        """
        Remove the resources of several kinds that match a label selector from :attr:`items`.

        :param kinds: The kinds, e.g. ``["ingress", "service"]``.
        :param namespace: The namespace.
        :param selector: An equality label selector (see :func:`matches_selector`).
        :returns: True.
        """
        for kind in kinds:
            matching = self.list_resources(kind, namespace, selector)
            for item in matching:
                self.items[kind].remove(item)
        return True

    def get_pod_logs(
        self, namespace: str, selector: str, container: Optional[str] = None, tail: int = 200
    ) -> Optional[str]:
        """
        Return no log lines: the in-memory cluster runs no pods.

        :param namespace: Ignored.
        :param selector: Ignored.
        :param container: Ignored.
        :param tail: Ignored.
        :returns: An empty string.
        """
        return ""


_kubernetes_factory: Optional[Callable[[], KubernetesService]] = None
_kubernetes: Optional[KubernetesService] = None


def configure_kubernetes(factory: Optional[Callable[[], KubernetesService]]) -> None:
    """
    Set the factory of the Kubernetes service that :func:`get_kubernetes` returns.

    :param factory: Returns the service, or None to restore the default,
        :class:`KubectlKubernetesService` with the configured cloud provider.
    """
    global _kubernetes_factory, _kubernetes  # pylint: disable=global-statement
    _kubernetes_factory = factory
    _kubernetes = None


def get_kubernetes() -> KubernetesService:
    """
    Return the Kubernetes service.

    It is created once, and again if the cloud provider is reconfigured, so that it keeps its
    readiness, rather than configuring kubectl for each call.
    """
    global _kubernetes  # pylint: disable=global-statement
    if _kubernetes_factory is not None:
        if _kubernetes is None:
            _kubernetes = _kubernetes_factory()
        return _kubernetes

    # pylint: disable=import-outside-toplevel
    from ..providers import get_provider

    provider = get_provider()
    if not isinstance(_kubernetes, KubectlKubernetesService) or _kubernetes.provider is not provider:
        _kubernetes = KubectlKubernetesService(provider=provider)
    return _kubernetes


__all__ = [
    "InMemoryKubernetesService",
    "KubectlKubernetesService",
    "KubernetesService",
    "billable_resources",
    "configure_kubernetes",
    "get_kubernetes",
    "manifest_kinds",
    "matches_selector",
    "redacted_manifest",
]
