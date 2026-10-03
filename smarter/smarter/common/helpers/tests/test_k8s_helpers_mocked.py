"""
Test KubernetesHelper's readiness, kubeconfig, namespace, ingress, certificate and secret methods.

kubectl and the aws cli are never called: subprocess is mocked. The container's
kubeconfig points at a real EKS cluster, so every test that reaches a subprocess
call must patch it.
"""

import subprocess
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.common.conf import smarter_settings
from smarter.common.helpers.k8s_helpers import (
    KubernetesHelper,
    KubernetesHelperException,
    kubernetes_helper,
)
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.common.helpers.k8s_helpers"
ERROR = subprocess.CalledProcessError(1, "kubectl")


def certificate(status: str) -> str:
    return json.dumps(
        {"status": {"conditions": [{"type": "Issuing", "status": "False"}, {"type": "Ready", "status": status}]}}
    )


class KubernetesHelperTestBase(SmarterTestBase):
    """Restore the singleton's state after each test, and refuse any unpatched subprocess call."""

    def setUp(self):
        super().setUp()
        self.helper = kubernetes_helper
        state = (
            self.helper._configured,
            self.helper._namespace_verified,
            self.helper._kubeconfig,
        )  # pylint: disable=protected-access

        def restore():
            self.helper._configured, self.helper._namespace_verified, self.helper._kubeconfig = (
                state  # pylint: disable=protected-access
            )

        self.addCleanup(restore)
        for name in ("check_output", "check_call", "Popen"):
            patcher = patch(f"{MODULE}.subprocess.{name}", side_effect=AssertionError(f"unpatched subprocess.{name}"))
            patcher.start()
            self.addCleanup(patcher.stop)

    def ready(self, value: bool = True):
        patcher = patch.object(KubernetesHelper, "ready", new_callable=PropertyMock, return_value=value)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestKubernetesHelperReady(KubernetesHelperTestBase):
    """Test ready, configured, namespace_verified, kubeconfig and update_kubeconfig()."""

    def test_singleton(self):
        self.assertIs(KubernetesHelper(), kubernetes_helper)

    def test_not_ready_without_aws(self):
        with patch(f"{MODULE}.aws_helper") as aws_helper:
            aws_helper.ready = False
            self.assertFalse(self.helper.ready)

    def test_not_ready_unconfigured(self):
        self.helper._configured = False  # pylint: disable=protected-access
        with (
            patch(f"{MODULE}.aws_helper") as aws_helper,
            patch.object(KubernetesHelper, "update_kubeconfig", return_value=False),
        ):
            aws_helper.ready = True
            self.assertFalse(self.helper.ready)

    def test_not_ready_without_namespace(self):
        self.helper._configured = True  # pylint: disable=protected-access
        self.helper._namespace_verified = False  # pylint: disable=protected-access
        with (
            patch(f"{MODULE}.aws_helper") as aws_helper,
            patch.object(KubernetesHelper, "verify_namespace", return_value=False),
        ):
            aws_helper.ready = True
            self.assertFalse(self.helper.ready)

    def test_ready(self):
        self.helper._configured = True  # pylint: disable=protected-access
        self.helper._namespace_verified = False  # pylint: disable=protected-access
        with (
            patch(f"{MODULE}.aws_helper") as aws_helper,
            patch.object(KubernetesHelper, "verify_namespace", return_value=True) as verify,
        ):
            aws_helper.ready = True
            self.assertTrue(self.helper.ready)
            self.assertTrue(self.helper.namespace_verified)
        verify.assert_called_once_with(smarter_settings.environment_namespace)

    def test_kubeconfig(self):
        self.assertTrue(self.helper.kubeconfig_path.endswith("/.kube/config"))
        self.helper._kubeconfig = None  # pylint: disable=protected-access
        with patch(f"{MODULE}.get_readonly_yaml_file", return_value={"apiVersion": "v1", "clusters": []}) as read:
            self.assertEqual(self.helper.kubeconfig, {"apiVersion": "v1", "clusters": []})
            self.assertEqual(self.helper.kubeconfig, {"apiVersion": "v1", "clusters": []})
        read.assert_called_once_with(self.helper.kubeconfig_path)

    def test_update_kubeconfig(self):
        self.helper._configured = False  # pylint: disable=protected-access
        with patch(f"{MODULE}.subprocess.check_call", return_value=0) as check_call:
            self.assertTrue(self.helper.configured)
        command = check_call.call_args.args[0]
        self.assertEqual(command[:3], ["aws", "eks", "update-kubeconfig"])
        self.assertIn(smarter_settings.aws_eks_cluster_name, command)

    def test_update_kubeconfig_errors(self):
        for error in (ERROR, OSError("aws not found")):
            with self.subTest(error=type(error).__name__), patch(f"{MODULE}.subprocess.check_call", side_effect=error):
                self.assertFalse(self.helper.update_kubeconfig())
                self.assertFalse(self.helper._configured)  # pylint: disable=protected-access

    def test_update_kubeconfig_without_settings(self):
        for field in ("aws_eks_cluster_name", "aws_region"):
            settings = MagicMock(aws_eks_cluster_name="cluster", aws_region="us-east-1")
            setattr(settings, field, None)
            with self.subTest(field=field), patch(f"{MODULE}.smarter_settings", settings):
                self.assertFalse(self.helper.update_kubeconfig())


class TestKubernetesHelperNamespace(KubernetesHelperTestBase):
    """Test verify_namespace() and get_namespaces()."""

    def test_verify_namespace(self):
        self.helper._configured = True  # pylint: disable=protected-access
        with patch(f"{MODULE}.subprocess.check_output", return_value=json.dumps({"kind": "Namespace"})) as check_output:
            self.assertTrue(self.helper.verify_namespace("ns"))
        self.assertEqual(check_output.call_args.args[0][:4], ["kubectl", "get", "namespace", "ns"])
        with patch(f"{MODULE}.subprocess.check_output", side_effect=ERROR):
            self.assertFalse(self.helper.verify_namespace("ns"))
        with patch(f"{MODULE}.subprocess.check_output", return_value="not json"):
            self.assertFalse(self.helper.verify_namespace("ns"))

    def test_verify_namespace_unconfigured(self):
        self.helper._configured = False  # pylint: disable=protected-access
        with patch.object(KubernetesHelper, "update_kubeconfig", return_value=False):
            self.assertFalse(self.helper.verify_namespace("ns"))

    def test_get_namespaces(self):
        self.ready()
        with patch(f"{MODULE}.subprocess.check_output", return_value=json.dumps({"items": []})):
            self.assertEqual(self.helper.get_namespaces(), {"items": []})


class TestKubernetesHelperIngress(KubernetesHelperTestBase):
    """Test the ingress, certificate and secret methods, and apply_manifest()."""

    def setUp(self):
        super().setUp()
        self.ready()

    def test_verify_ingress_and_secret(self):
        for method in (self.helper.verify_ingress, self.helper.verify_secret):
            with self.subTest(method=method.__name__):
                with patch(f"{MODULE}.subprocess.check_output", return_value=json.dumps({"kind": "x"})):
                    self.assertTrue(method("a", "ns"))
                with patch(f"{MODULE}.subprocess.check_output", side_effect=ERROR):
                    self.assertFalse(method("a", "ns"))
                with patch(f"{MODULE}.subprocess.check_output", return_value="not json"):
                    self.assertFalse(method("a", "ns"))

    def test_verify_certificate(self):
        """Test that a certificate is verified only when its Ready condition is True."""
        cases = [
            (certificate("True"), True),
            (certificate("False"), False),
            (json.dumps({"status": {}}), False),
            ("not json", False),
        ]
        for output, expected in cases:
            with self.subTest(output=output), patch(f"{MODULE}.subprocess.check_output", return_value=output):
                self.assertEqual(self.helper.verify_certificate("a-tls", "ns"), expected)
        with patch(f"{MODULE}.subprocess.check_output", side_effect=ERROR):
            self.assertFalse(self.helper.verify_certificate("a-tls", "ns"))

    def test_verify_ingress_resources(self):
        """Test that the ingress, secret and certificate are verified, waiting for the certificate."""
        with (
            patch.object(KubernetesHelper, "verify_ingress", return_value=True),
            patch.object(KubernetesHelper, "verify_secret", return_value=True) as verify_secret,
            patch.object(KubernetesHelper, "verify_certificate", side_effect=[False, True]) as verify_certificate,
            patch(f"{MODULE}.time.sleep") as sleep,
        ):
            self.assertEqual(self.helper.verify_ingress_resources("bot.example.com", "ns"), (True, True, True))
        verify_secret.assert_called_once_with("bot.example.com-tls", "ns")
        self.assertEqual(verify_certificate.call_count, 2)
        sleep.assert_called_once()

    def test_verify_ingress_resources_certificate_timeout(self):
        with (
            patch.object(KubernetesHelper, "verify_ingress", return_value=True),
            patch.object(KubernetesHelper, "verify_secret", return_value=False),
            patch.object(KubernetesHelper, "verify_certificate", return_value=False),
            patch(f"{MODULE}.time.sleep") as sleep,
        ):
            self.assertEqual(self.helper.verify_ingress_resources("bot.example.com", "ns"), (True, False, False))
        self.assertEqual(sleep.call_count, 30)

    def test_delete(self):
        """Test that each delete method runs kubectl delete, and returns False on an error."""
        for method, kind in (
            (self.helper.delete_ingress, "ingress"),
            (self.helper.delete_certificate, "certificate"),
            (self.helper.delete_secret, "secret"),
        ):
            with self.subTest(kind=kind):
                with patch(f"{MODULE}.subprocess.check_call", return_value=0) as check_call:
                    self.assertTrue(method("a", "ns"))
                self.assertEqual(check_call.call_args.args[0], ["kubectl", "delete", kind, "a", "-n", "ns"])
                for error in (ERROR, OSError("kubectl not found")):
                    with patch(f"{MODULE}.subprocess.check_call", side_effect=error):
                        self.assertFalse(method("a", "ns"))

    def test_delete_ingress_resources(self):
        with patch(f"{MODULE}.subprocess.check_call", return_value=0) as check_call:
            self.assertEqual(self.helper.delete_ingress_resources("bot.example.com", "ns"), (True, True, True))
        names = [call.args[0][3] for call in check_call.call_args_list]
        self.assertEqual(names, ["bot.example.com", "bot.example.com-tls", "bot.example.com-tls"])

    def test_apply_manifest(self):
        process = MagicMock(returncode=0)
        process.communicate.return_value = (b"", b"")
        process.__enter__.return_value = process
        with patch(f"{MODULE}.subprocess.Popen", return_value=process) as popen:
            self.helper.apply_manifest("kind: Namespace")
        self.assertEqual(popen.call_args.args[0], ["kubectl", "apply", "-f", "-"])
        process.communicate.assert_called_once_with(input=b"kind: Namespace")

        process.returncode = 1
        process.communicate.return_value = (b"", b"error: invalid")
        with patch(f"{MODULE}.subprocess.Popen", return_value=process):
            with self.assertRaises(KubernetesHelperException):
                self.helper.apply_manifest("kind: Namespace")

    def test_not_ready(self):
        """Test that nothing calls kubectl when the helper is not ready."""
        with patch.object(KubernetesHelper, "ready", new_callable=PropertyMock, return_value=False):
            self.assertIsNone(self.helper.apply_manifest("kind: Namespace"))
            self.assertIsNone(self.helper.get_namespaces())
            for method in (
                self.helper.verify_ingress,
                self.helper.verify_certificate,
                self.helper.verify_secret,
                self.helper.delete_ingress,
                self.helper.delete_certificate,
                self.helper.delete_secret,
            ):
                with self.subTest(method=method.__name__):
                    self.assertFalse(method("a", "ns"))
