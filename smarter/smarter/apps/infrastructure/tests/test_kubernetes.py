"""
Test :mod:`smarter.apps.infrastructure.services.kubernetes`.

kubectl never runs: ``subprocess.run`` is replaced by :class:`FakeKubectl`, which answers like
kubectl, and the kubeconfig comes from the in-memory provider.
"""

import subprocess
from typing import Optional
from unittest.mock import patch

from smarter.apps.infrastructure.exceptions import (
    InfrastructureConfigurationError,
    KubernetesServiceError,
)
from smarter.apps.infrastructure.services import (
    KubectlKubernetesService,
    configure_kubernetes,
    get_kubernetes,
    infrastructure,
)
from smarter.apps.infrastructure.services.kubernetes import (
    billable_resources,
    manifest_kinds,
)
from smarter.apps.infrastructure.signals import (
    billable_resource_created,
    billable_resource_creating,
    billable_resource_destroyed,
    infrastructure_connected,
    infrastructure_connection_failed,
    resource_applied,
)
from smarter.lib import json

from .base import InfrastructureTestBase

MODULE = "smarter.apps.infrastructure.services.kubernetes"
NAMESPACE = "smarter-platform-test"

INGRESS_MANIFEST = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app.example.com
"""

QDRANT_MANIFEST = """
apiVersion: v1
kind: Service
metadata:
  name: qdrant
spec:
  type: ClusterIP
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
spec:
  volumeClaimTemplates:
  - metadata:
      name: storage
---
apiVersion: v1
kind: Service
metadata:
  name: public
spec:
  type: LoadBalancer
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: models
"""


def completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["kubectl"], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeKubectl:
    """Answers kubectl commands from a dict of resources, keyed by (kind, name)."""

    def __init__(self):
        self.resources: dict[tuple[str, str], dict] = {("namespace", NAMESPACE): {"kind": "Namespace"}}
        self.commands: list[list[str]] = []
        self.applied: list[str] = []
        self.fail: Optional[str] = None

    def __call__(self, command, input=None, **kwargs):  # pylint: disable=redefined-builtin
        self.commands.append(command)
        args = command[1:]
        if self.fail:
            return completed(1, stderr=self.fail)
        verb = args[0]
        if verb == "apply":
            self.applied.append(input)
            return completed(stdout="applied")
        if verb == "get":
            kind, rest = args[1], args[2:]
            if rest and not rest[0].startswith("-"):
                resource = self.resources.get((kind, rest[0]))
                if resource is None:
                    if "--ignore-not-found" in rest:
                        return completed(stdout="")
                    return completed(1, stderr=f'{kind} "{rest[0]}" not found')
                return completed(stdout=json.dumps(resource))
            items = [r for (k, _), r in self.resources.items() if k == kind]
            return completed(stdout=json.dumps({"items": items}))
        if verb == "delete":
            for kind in args[1].split(","):
                if len(args) > 2 and not args[2].startswith("-"):
                    self.resources.pop((kind, args[2]), None)
            return completed()
        if verb == "logs":
            return completed(stdout="line 1\nline 2\n")
        return completed(1, stderr=f"unknown command {verb}")


class KubernetesTestBase(InfrastructureTestBase):
    def setUp(self):
        super().setUp()
        self.kubectl = FakeKubectl()
        patcher = patch(f"{MODULE}.subprocess.run", side_effect=self.kubectl)
        patcher.start()
        self.addCleanup(patcher.stop)
        settings = patch(f"{MODULE}.smarter_settings")
        self.settings = settings.start()
        self.settings.environment_namespace = NAMESPACE
        self.settings.data_directory = "/tmp"  # nosec B108
        self.addCleanup(settings.stop)
        self.kubernetes = KubectlKubernetesService(provider=self.provider, allow_in_tests=True)


class TestKubernetesReadiness(KubernetesTestBase):
    """Test that the cluster is ready once kubectl is configured and the namespace exists."""

    def test_ready(self):
        events = self.capture(infrastructure_connected, infrastructure_connection_failed)
        self.assertTrue(self.kubernetes.ready)
        self.assertTrue(self.kubernetes.ready)
        # the kubeconfig is written once, and connected is sent once.
        self.assertEqual(self.provider.kubeconfig_updates, 1)
        self.assertEqual(len(self.sent(events, infrastructure_connected)), 1)

    def test_not_configured(self):
        events = self.capture(infrastructure_connection_failed)
        self.provider.ready = False
        self.assertFalse(self.kubernetes.ready)
        self.assertIn("not configured", self.sent(events, infrastructure_connection_failed)[0]["error"])

    def test_namespace_missing(self):
        del self.kubectl.resources[("namespace", NAMESPACE)]
        self.assertFalse(self.kubernetes.ready)
        self.assertFalse(self.kubernetes.verify_namespace(NAMESPACE))

    def test_without_provider(self):
        """A cluster whose kubeconfig is already in place needs no provider."""
        kubernetes = KubectlKubernetesService(allow_in_tests=True)
        self.assertEqual(kubernetes.provider_name, "kubectl")
        self.assertTrue(kubernetes.ready)

    def test_refused_in_unit_tests(self):
        """Kubectl is refused in the unit tests, unless allowed: the containers' kubeconfig is real."""
        kubernetes = KubectlKubernetesService(provider=self.provider)
        self.assertFalse(kubernetes.ready)
        with self.assertRaises(InfrastructureConfigurationError):
            kubernetes._kubectl("version")  # pylint: disable=protected-access
        self.assertEqual(self.kubectl.commands, [])

    def test_provider_refuses_kubeconfig(self):
        with patch.object(self.provider, "update_kubeconfig", side_effect=InfrastructureConfigurationError("no")):
            self.assertFalse(self.kubernetes.configured)

    def test_kubeconfig(self):
        self.assertEqual(self.kubernetes.kubeconfig_path, "/tmp/.kube/config")  # nosec B108
        with patch(f"{MODULE}.get_readonly_yaml_file", return_value={"apiVersion": "v1"}) as read:
            self.assertEqual(self.kubernetes.kubeconfig, {"apiVersion": "v1"})
            self.assertEqual(self.kubernetes.kubeconfig, {"apiVersion": "v1"})
        read.assert_called_once()

    def test_invalid_json(self):
        with patch(f"{MODULE}.subprocess.run", return_value=completed(stdout="{not json")):
            self.assertIsNone(self.kubernetes._kubectl_json("get", "x"))  # pylint: disable=protected-access


class TestKubernetesResources(KubernetesTestBase):
    """Test the resource operations."""

    def test_apply_manifest(self):
        events = self.capture(resource_applied, billable_resource_creating)
        self.kubernetes.apply_manifest(INGRESS_MANIFEST)
        self.assertEqual(self.kubectl.applied, [INGRESS_MANIFEST])
        self.assertEqual(self.sent(events, resource_applied)[0]["kinds"], ["Ingress"])
        self.assertEqual(self.sent(events, billable_resource_creating), [])

    def test_apply_billable_manifest(self):
        """A manifest's volumes and load balancers are announced as billable resources."""
        events = self.capture(billable_resource_creating, billable_resource_created)
        self.kubernetes.apply_manifest(QDRANT_MANIFEST)
        created = [(e["resource_type"], e["resource_name"]) for e in self.sent(events, billable_resource_created)]
        self.assertEqual(
            created,
            [
                ("kubernetes.statefulset", "qdrant"),
                ("kubernetes.service", "public"),
                ("kubernetes.persistentvolumeclaim", "models"),
            ],
        )
        self.assertEqual(len(self.sent(events, billable_resource_creating)), 3)

    def test_apply_rejected(self):
        self.assertTrue(self.kubernetes.ready)
        self.kubectl.fail = "admission webhook denied"
        with self.assertRaises(KubernetesServiceError):
            self.kubernetes.apply_manifest(INGRESS_MANIFEST)

    def test_apply_when_not_ready(self):
        self.provider.ready = False
        self.assertIsNone(self.kubernetes.apply_manifest(INGRESS_MANIFEST))
        self.assertEqual(self.kubectl.applied, [])

    def test_get_and_list(self):
        self.kubectl.resources[("deployment", "app")] = {"kind": "Deployment", "metadata": {"name": "app"}}
        self.assertEqual(self.kubernetes.get_resource("deployment", "app", NAMESPACE)["kind"], "Deployment")
        self.assertIsNone(self.kubernetes.get_resource("deployment", "nope", NAMESPACE))
        self.assertEqual(len(self.kubernetes.list_resources("deployment", NAMESPACE, selector="app=x")), 1)
        list_command = self.kubectl.commands[-1]
        self.assertEqual(list_command[list_command.index("-l") + 1], "app=x")

    def test_delete(self):
        self.kubectl.resources[("ingress", "app.example.com")] = {"kind": "Ingress"}
        self.assertTrue(self.kubernetes.delete_ingress("app.example.com", NAMESPACE))
        self.assertNotIn(("ingress", "app.example.com"), self.kubectl.resources)
        self.assertTrue(self.kubernetes.delete_secret("app.example.com-tls", NAMESPACE))
        self.assertTrue(self.kubernetes.delete_certificate("app.example.com-tls", NAMESPACE))

    def test_delete_billable(self):
        events = self.capture(billable_resource_destroyed)
        self.assertTrue(self.kubernetes.delete_resource("persistentvolumeclaim", "models", NAMESPACE))
        self.assertTrue(self.kubernetes.delete_resources(["statefulset", "persistentvolumeclaim"], NAMESPACE, "a=b"))
        destroyed = [(e["resource_type"], e["resource_name"]) for e in self.sent(events, billable_resource_destroyed)]
        self.assertEqual(
            destroyed,
            [("kubernetes.persistentvolumeclaim", "models"), ("kubernetes.persistentvolumeclaim", "a=b")],
        )

    def test_delete_requires_a_selector(self):
        with self.assertRaises(KubernetesServiceError):
            self.kubernetes.delete_resources(["deployment"], NAMESPACE, "")

    def test_failures(self):
        self.assertTrue(self.kubernetes.ready)
        self.kubectl.fail = "forbidden"
        self.assertFalse(self.kubernetes.delete_resource("secret", "x", NAMESPACE))
        self.assertFalse(self.kubernetes.delete_resources(["secret"], NAMESPACE, "a=b"))
        self.assertIsNone(self.kubernetes.get_resource("secret", "x", NAMESPACE))
        self.assertEqual(self.kubernetes.list_resources("pods", NAMESPACE), [])
        self.assertIn("forbidden", self.kubernetes.get_pod_logs(NAMESPACE, "a=b"))

    def test_not_ready(self):
        self.provider.ready = False
        self.assertIsNone(self.kubernetes.get_resource("secret", "x", NAMESPACE))
        self.assertEqual(self.kubernetes.list_resources("pods", NAMESPACE), [])
        self.assertFalse(self.kubernetes.delete_resource("secret", "x", NAMESPACE))
        self.assertFalse(self.kubernetes.delete_resources(["secret"], NAMESPACE, "a=b"))
        self.assertIsNone(self.kubernetes.get_pod_logs(NAMESPACE, "a=b"))

    def test_get_pod_logs(self):
        self.assertEqual(self.kubernetes.get_pod_logs(NAMESPACE, "a=b", container="engine", tail=5), "line 1\nline 2\n")
        command = self.kubectl.commands[-1]
        self.assertEqual(command[-2:], ["-c", "engine"])
        self.assertIn("5", command)


class TestIngressResources(KubernetesTestBase):
    """Test the ingress operations that LLMClient deployments use."""

    def add_ingress(self, certificate_ready: str = "True"):
        hostname = "app.example.com"
        self.kubectl.resources[("ingress", hostname)] = {"kind": "Ingress"}
        self.kubectl.resources[("secret", f"{hostname}-tls")] = {"kind": "Secret"}
        self.kubectl.resources[("certificate", f"{hostname}-tls")] = {
            "kind": "Certificate",
            "status": {"conditions": [{"type": "Ready", "status": certificate_ready}]},
        }
        return hostname

    def test_verify_ingress_resources(self):
        hostname = self.add_ingress()
        self.assertEqual(
            self.kubernetes.verify_ingress_resources(hostname, NAMESPACE, max_attempts=1), (True, True, True)
        )

    def test_certificate_not_ready(self):
        """A certificate that is not issued is checked again, up to max_attempts times."""
        hostname = self.add_ingress(certificate_ready="False")
        with patch.object(self.kubernetes, "_sleep") as sleep:
            result = self.kubernetes.verify_ingress_resources(hostname, NAMESPACE, max_attempts=3)
        self.assertEqual(result, (True, False, True))
        self.assertEqual(sleep.call_count, 2)

    def test_missing_resources(self):
        self.assertEqual(
            self.kubernetes.verify_ingress_resources("missing.example.com", NAMESPACE, max_attempts=1),
            (False, False, False),
        )
        self.kubectl.resources[("certificate", "bare-tls")] = {"kind": "Certificate"}
        self.assertFalse(self.kubernetes.verify_certificate("bare-tls", NAMESPACE))

    def test_delete_ingress_resources(self):
        hostname = self.add_ingress()
        self.assertEqual(self.kubernetes.delete_ingress_resources(hostname, NAMESPACE), (True, True, True))
        self.assertEqual(set(self.kubectl.resources), {("namespace", NAMESPACE)})


class TestBillableResources(InfrastructureTestBase):
    """Test billable_resources() and manifest_kinds()."""

    def test_billable_resources(self):
        self.assertEqual(
            billable_resources(QDRANT_MANIFEST),
            [("statefulset", "qdrant"), ("service", "public"), ("persistentvolumeclaim", "models")],
        )
        self.assertEqual(billable_resources(INGRESS_MANIFEST), [])
        self.assertEqual(billable_resources("{not: [valid"), [])

    def test_manifest_kinds(self):
        self.assertEqual(
            manifest_kinds(QDRANT_MANIFEST), ["Service", "StatefulSet", "Service", "PersistentVolumeClaim"]
        )
        self.assertEqual(manifest_kinds("{not: [valid"), [])


class TestConfigureKubernetes(InfrastructureTestBase):
    """Test that the Kubernetes service can be replaced, and is kept between calls."""

    def test_default(self):
        kubernetes = get_kubernetes()
        self.assertIsInstance(kubernetes, KubectlKubernetesService)
        self.assertIs(kubernetes.provider, self.provider)
        self.assertIs(get_kubernetes(), kubernetes)
        self.assertIs(infrastructure.kubernetes, kubernetes)

    def test_rebuilt_for_another_provider(self):
        first = get_kubernetes()
        self.setUp_other_provider()
        self.assertIsNot(get_kubernetes(), first)

    def setUp_other_provider(self):  # pylint: disable=invalid-name
        # pylint: disable=import-outside-toplevel
        from smarter.apps.infrastructure.providers import configure_provider
        from smarter.apps.infrastructure.providers.memory import InMemoryProvider

        other = InMemoryProvider()
        configure_provider(lambda: other)

    def test_configure(self):
        fake = KubectlKubernetesService(allow_in_tests=True)
        configure_kubernetes(lambda: fake)
        self.assertIs(get_kubernetes(), fake)
        self.assertIs(get_kubernetes(), fake)
        configure_kubernetes(None)
        self.assertIsNot(get_kubernetes(), fake)
