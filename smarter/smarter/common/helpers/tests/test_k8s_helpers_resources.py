"""
Test KubernetesHelper's generic resource methods: get, list, delete and logs.

kubectl is never called: subprocess is mocked, and the helper is made ready.
"""

import subprocess
from unittest.mock import PropertyMock, patch

from smarter.common.helpers.k8s_helpers import (
    KubernetesHelper,
    KubernetesHelperException,
    kubernetes_helper,
)
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.common.helpers.k8s_helpers.subprocess"


class TestKubernetesHelperResources(SmarterTestBase):
    """Test get_resource(), list_resources(), delete_resources() and get_pod_logs()."""

    def setUp(self):
        super().setUp()
        patcher = patch.object(KubernetesHelper, "ready", new_callable=PropertyMock, return_value=True)
        self.ready_mock = patcher.start()
        self.addCleanup(patcher.stop)
        self.helper = kubernetes_helper

    def test_get_resource(self):
        """Test that a resource is returned as a dict, and a missing one as None."""
        with patch(f"{MODULE}.check_output", return_value=json.dumps({"kind": "Deployment"})) as check_output:
            self.assertEqual(self.helper.get_resource("deployment", "a", "ns"), {"kind": "Deployment"})
        command = check_output.call_args.args[0]
        self.assertEqual(command[:4], ["kubectl", "get", "deployment", "a"])
        self.assertIn("--ignore-not-found", command)
        with patch(f"{MODULE}.check_output", return_value=""):
            self.assertIsNone(self.helper.get_resource("deployment", "a", "ns"))
        with patch(f"{MODULE}.check_output", side_effect=subprocess.CalledProcessError(1, "kubectl")):
            self.assertIsNone(self.helper.get_resource("deployment", "a", "ns"))

    def test_list_resources(self):
        """Test that the items are returned, filtered by the label selector."""
        output = json.dumps({"items": [{"kind": "Pod"}, {"kind": "Pod"}]})
        with patch(f"{MODULE}.check_output", return_value=output) as check_output:
            self.assertEqual(len(self.helper.list_resources("pods", "ns", "a=b")), 2)
        self.assertEqual(check_output.call_args.args[0][-2:], ["-l", "a=b"])
        with patch(f"{MODULE}.check_output", side_effect=subprocess.CalledProcessError(1, "kubectl")):
            self.assertEqual(self.helper.list_resources("pods", "ns", "a=b"), [])

    def test_delete_resources(self):
        """Test that several kinds are deleted by selector, idempotently, and that a selector is required."""
        with patch(f"{MODULE}.check_call") as check_call:
            self.assertTrue(self.helper.delete_resources(["deployment", "service"], "ns", "a=b"))
        command = check_call.call_args.args[0]
        self.assertEqual(command[:3], ["kubectl", "delete", "deployment,service"])
        self.assertIn("--ignore-not-found", command)
        with patch(f"{MODULE}.check_call", side_effect=subprocess.CalledProcessError(1, "kubectl")):
            self.assertFalse(self.helper.delete_resources(["deployment"], "ns", "a=b"))
        with self.assertRaises(KubernetesHelperException):
            self.helper.delete_resources(["deployment"], "ns", "")

    def test_get_pod_logs(self):
        """Test that logs are returned, with the container and tail."""
        with patch(f"{MODULE}.check_output", return_value="hello\n") as check_output:
            self.assertEqual(self.helper.get_pod_logs("ns", "a=b", container="engine", tail=5), "hello\n")
        command = check_output.call_args.args[0]
        self.assertIn("--tail", command)
        self.assertEqual(command[-2:], ["-c", "engine"])

    def test_not_ready(self):
        """Test that an unavailable cluster is never called."""
        self.ready_mock.return_value = False
        with patch(f"{MODULE}.check_output") as check_output, patch(f"{MODULE}.check_call") as check_call:
            self.assertIsNone(self.helper.get_resource("deployment", "a", "ns"))
            self.assertEqual(self.helper.list_resources("pods", "ns"), [])
            self.assertFalse(self.helper.delete_resources(["deployment"], "ns", "a=b"))
            self.assertIsNone(self.helper.get_pod_logs("ns", "a=b"))
        check_output.assert_not_called()
        check_call.assert_not_called()
