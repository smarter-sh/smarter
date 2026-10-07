"""Test the cluster backends: :mod:`smarter.apps.llmhost.services.cluster`."""

from unittest.mock import MagicMock

import yaml

from smarter.apps.infrastructure.exceptions import KubernetesServiceError
from smarter.apps.llmhost.services.cluster import (
    InMemoryClusterBackend,
    KubectlClusterBackend,
    configure_cluster,
    get_cluster,
)
from smarter.apps.llmhost.services.exceptions import LLMHostClusterError
from smarter.lib.unittest.base_classes import SmarterTestBase


def resource(kind: str, name: str, llmhost: str = "llmhost-1-a") -> dict:
    return {"apiVersion": "v1", "kind": kind, "metadata": {"name": name, "labels": {"smarter.sh/llmhost": llmhost}}}


class TestInMemoryClusterBackend(SmarterTestBase):
    """Test the in-memory cluster, which the other tests rely on."""

    def setUp(self):
        super().setUp()
        self.cluster = InMemoryClusterBackend(namespace="ns")

    def test_apply_get_list(self):
        """Test that applied resources can be read back, by name and by label selector, with kinds normalized."""
        self.cluster.apply([resource("Deployment", "llmhost-1-a"), resource("Service", "llmhost-1-a")])
        self.cluster.apply([resource("Deployment", "llmhost-2-b", llmhost="llmhost-2-b")])
        self.assertEqual(self.cluster.get("deployment", "llmhost-1-a")["kind"], "Deployment")
        self.assertIsNone(self.cluster.get("deployment", "missing"))
        self.assertEqual(len(self.cluster.list_resources("deployments", "smarter.sh/llmhost=llmhost-1-a")), 1)
        self.assertEqual(len(self.cluster.applied), 2)

    def test_apply_keeps_status(self):
        """Test that re-applying a resource keeps its status, as a real cluster does."""
        self.cluster.apply([resource("Deployment", "d")])
        self.cluster.set_deployment_status("d", readyReplicas=1)
        self.cluster.apply([resource("Deployment", "d")])
        self.assertEqual(self.cluster.get("deployment", "d")["status"], {"readyReplicas": 1})

    def test_delete(self):
        """Test that delete removes only the selected kinds and labels, and delete_named one resource."""
        self.cluster.apply(
            [
                resource("Deployment", "a"),
                resource("PersistentVolumeClaim", "a-models"),
                resource("Deployment", "b", llmhost="other"),
            ]
        )
        self.assertTrue(self.cluster.delete(["deployment"], "smarter.sh/llmhost=llmhost-1-a"))
        self.assertIsNone(self.cluster.get("deployment", "a"))
        self.assertIsNotNone(self.cluster.get("persistentvolumeclaim", "a-models"))
        self.assertIsNotNone(self.cluster.get("deployment", "b"))
        self.assertTrue(self.cluster.delete_named("persistentvolumeclaim", "a-models"))
        self.assertFalse(self.cluster.delete_named("secret", "missing"))

    def test_not_ready(self):
        """Test that an unavailable cluster rejects changes, and has no logs."""
        self.cluster.ready = False
        with self.assertRaises(LLMHostClusterError):
            self.cluster.apply([resource("Deployment", "a")])
        with self.assertRaises(LLMHostClusterError):
            self.cluster.delete(["deployment"], "a=b")
        self.assertIsNone(self.cluster.logs("a=b"))

    def test_fail_apply(self):
        """Test the simulation of a cluster that rejects resources."""
        self.cluster.fail_apply = "admission webhook denied"
        with self.assertRaisesRegex(LLMHostClusterError, "admission webhook"):
            self.cluster.apply([resource("Deployment", "a")])

    def test_logs(self):
        """Test that logs returns the last lines."""
        self.cluster.pod_logs = "\n".join(f"line {i}" for i in range(10))
        self.assertEqual(self.cluster.logs("a=b", tail=2), "line 8\nline 9")


class TestKubectlClusterBackend(SmarterTestBase):
    """Test that the kubectl backend delegates to the Kubernetes service, with a mock service."""

    def setUp(self):
        super().setUp()
        self.helper = MagicMock()
        self.helper.ready = True
        self.cluster = KubectlClusterBackend(namespace="ns", helper=self.helper)

    def test_apply(self):
        """Test that resources are applied as one multi-document YAML manifest."""
        self.cluster.apply([resource("Deployment", "a"), resource("Service", "a")])
        manifest = self.helper.apply_manifest.call_args.args[0]
        self.assertEqual([doc["kind"] for doc in yaml.safe_load_all(manifest)], ["Deployment", "Service"])

    def test_apply_errors(self):
        """Test that an unavailable or rejecting cluster raises LLMHostClusterError."""
        self.helper.apply_manifest.side_effect = KubernetesServiceError("denied")
        with self.assertRaisesRegex(LLMHostClusterError, "denied"):
            self.cluster.apply([resource("Deployment", "a")])
        self.helper.ready = False
        with self.assertRaises(LLMHostClusterError):
            self.cluster.apply([resource("Deployment", "a")])
        with self.assertRaises(LLMHostClusterError):
            self.cluster.delete(["deployment"], "a=b")

    def test_delegation(self):
        """Test that get, list, delete and logs call the helper in the backend's namespace."""
        self.cluster.get("deployment", "a")
        self.helper.get_resource.assert_called_with("deployment", "a", "ns")
        self.cluster.list_resources("pods", "a=b")
        self.helper.list_resources.assert_called_with("pods", "ns", "a=b")
        self.cluster.delete(["deployment", "service"], "a=b")
        self.helper.delete_resources.assert_called_with(["deployment", "service"], "ns", "a=b")
        self.cluster.logs("a=b", container="engine", tail=5)
        self.helper.get_pod_logs.assert_called_with("ns", "a=b", container="engine", tail=5)

    def test_delete_named(self):
        """Test that delete_named supports secrets and ingresses."""
        self.cluster.delete_named("secret", "a-tls")
        self.helper.delete_secret.assert_called_with("a-tls", "ns")
        self.cluster.delete_named("ingress", "a")
        self.helper.delete_ingress.assert_called_with("a", "ns")
        with self.assertRaises(LLMHostClusterError):
            self.cluster.delete_named("deployment", "a")


class TestConfigureCluster(SmarterTestBase):
    """Test configure_cluster() and get_cluster()."""

    def tearDown(self):
        configure_cluster(None)
        super().tearDown()

    def test_configure(self):
        """Test that the default backend is kubectl, and that a factory replaces it."""
        self.assertIsInstance(get_cluster(), KubectlClusterBackend)
        fake = InMemoryClusterBackend()
        configure_cluster(lambda: fake)
        self.assertIs(get_cluster(), fake)
        configure_cluster(None)
        self.assertIsInstance(get_cluster(), KubectlClusterBackend)
