"""Test status interpretation, health checks and reporting: :mod:`smarter.apps.llmhost.services.observability`."""

import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests

from smarter.apps.llmhost.services.observability import (
    HealthProber,
    LLMHostObservation,
    build_report,
    in_cluster,
    interpret,
    summarize_pod,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


def deployment(replicas: int = 1, ready: int = 0, conditions=None) -> dict:
    return {"spec": {"replicas": replicas}, "status": {"readyReplicas": ready, "conditions": conditions or []}}


def pod(
    phase="Running", ready=False, waiting=None, init_running=False, unschedulable=None, restarts=0, oom=False
) -> dict:
    state = {"waiting": {"reason": waiting, "message": "details"}} if waiting else {"running": {}}
    container = {"name": "engine", "ready": ready, "restartCount": restarts, "state": state}
    if oom:
        container["lastState"] = {"terminated": {"reason": "OOMKilled"}}
    status = {"phase": phase, "containerStatuses": [container]}
    if init_running:
        status["initContainerStatuses"] = [{"name": "download-model", "state": {"running": {}}}]
        status["containerStatuses"] = [
            {"name": "engine", "ready": False, "state": {"waiting": {"reason": "PodInitializing"}}}
        ]
    if unschedulable:
        status = {
            "phase": "Pending",
            "conditions": [
                {"type": "PodScheduled", "status": "False", "reason": "Unschedulable", "message": unschedulable}
            ],
        }
    return {"metadata": {"name": "llmhost-1-a-xyz"}, "status": status}


class TestInterpret(SmarterTestBase):
    """Test that Kubernetes state maps to the right LLMHost status."""

    def test_inactive(self):
        self.assertEqual(interpret(None, [])[0], "inactive")

    def test_active(self):
        status, message, replicas, ready = interpret(deployment(1, 1), [pod(ready=True)])
        self.assertEqual((status, replicas, ready), ("active", 1, 1))
        self.assertIn("1/1", message)

    def test_degraded(self):
        status, message, _, _ = interpret(deployment(2, 1), [pod(ready=True), pod(waiting="CrashLoopBackOff")])
        self.assertEqual(status, "degraded")
        self.assertIn("CrashLoopBackOff", message)

    def test_error(self):
        """Test that unrecoverable container states are errors."""
        for reason in ("ImagePullBackOff", "ErrImagePull", "CrashLoopBackOff", "CreateContainerConfigError"):
            with self.subTest(reason=reason):
                status, message, _, _ = interpret(deployment(), [pod(waiting=reason)])
                self.assertEqual(status, "error")
                self.assertIn(reason, message)

    def test_progress_deadline(self):
        condition = {"type": "Progressing", "reason": "ProgressDeadlineExceeded", "message": "too slow"}
        self.assertEqual(interpret(deployment(conditions=[condition]), [pod()])[:2], ("error", "too slow"))

    def test_downloading(self):
        self.assertEqual(interpret(deployment(), [pod(phase="Pending", init_running=True)])[0], "downloading")

    def test_pending(self):
        """Test that unschedulable pods, e.g. waiting for a GPU node, and missing pods are pending."""
        status, message, _, _ = interpret(deployment(), [pod(unschedulable="0/3 nodes have nvidia.com/gpu")])
        self.assertEqual(status, "pending")
        self.assertIn("nvidia.com/gpu", message)
        self.assertEqual(interpret(deployment(), [])[0], "pending")

    def test_deploying(self):
        """Test that a running, unready server is deploying, i.e. downloading or loading weights."""
        self.assertEqual(interpret(deployment(), [pod()])[0], "deploying")

    def test_summarize_pod(self):
        summary = summarize_pod(pod(ready=True, restarts=2))
        self.assertEqual(
            summary,
            {
                "name": "llmhost-1-a-xyz",
                "phase": "Running",
                "ready": True,
                "restarts": 2,
                "downloading": False,
                "reason": None,
            },
        )
        self.assertIn("OOMKilled", summarize_pod(pod(oom=True))["reason"])
        self.assertIn("Unschedulable", summarize_pod(pod(unschedulable="no gpu"))["reason"])
        self.assertTrue(summarize_pod(pod(init_running=True))["downloading"])

    def test_observation_to_dict(self):
        now = datetime.datetime(2026, 1, 1)
        data = LLMHostObservation(status="active", ready_replicas=1, replicas=1, checked_at=now).to_dict()
        self.assertEqual(data["readyReplicas"], 1)
        self.assertEqual(data["checkedAt"], now.isoformat())
        self.assertIsNone(LLMHostObservation(status="inactive").to_dict()["checkedAt"])


class TestHealthProber(SmarterTestBase):
    """Test HealthProber, with requests mocked."""

    def test_disabled(self):
        """Test that probing outside the cluster, where Services are unreachable, returns None."""
        with patch("smarter.apps.llmhost.services.observability.requests.get") as get:
            self.assertIsNone(HealthProber(enabled=False).check("http://x/health"))
            self.assertIsNone(HealthProber(enabled=True).check(""))
        get.assert_not_called()

    def test_enabled(self):
        prober = HealthProber(enabled=True)
        with patch("smarter.apps.llmhost.services.observability.requests.get") as get:
            get.return_value = MagicMock(status_code=200)
            self.assertTrue(prober.check("http://x/health", api_key="k"))
            self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer k"})
            get.return_value = MagicMock(status_code=503)
            self.assertFalse(prober.check("http://x/health"))
            get.side_effect = requests.ConnectionError("refused")
            self.assertFalse(prober.check("http://x/health"))

    def test_in_cluster(self):
        with patch.dict("os.environ", {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}):
            self.assertTrue(in_cluster())
            self.assertTrue(HealthProber().enabled)
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(in_cluster())


def host(name, status, engine="vllm", gpus=1, replicas=1, cost_per_hour=None, estimated_cost=None, deployed=True):
    return SimpleNamespace(
        name=name,
        user_profile=SimpleNamespace(user=SimpleNamespace(username="owner")),
        status=status,
        inference_engine=engine,
        model_repository="org/model",
        model_task="text-generation",
        replicas=replicas,
        ready_replicas=replicas if status == "active" else 0,
        gpu_count=gpus,
        gpu_type="A10G",
        endpoint_url="http://x/v1",
        public_url="",
        deployed_at=None,
        uptime_hours=2.0 if deployed else None,
        cost_per_hour=cost_per_hour,
        estimated_cost=estimated_cost,
        is_deployed=deployed,
    )


class TestReport(SmarterTestBase):
    """Test build_report()."""

    def test_report(self):
        report = build_report(
            [
                host("a", "active", gpus=2, replicas=2, cost_per_hour=Decimal("2.5"), estimated_cost=Decimal("5.0")),
                host("b", "error", engine="tgi"),
                host("c", "inactive", engine="ollama", gpus=0, deployed=False),
            ]
        )
        totals = report["totals"]
        self.assertEqual((totals["llmhosts"], totals["deployed"], totals["active"], totals["errors"]), (3, 2, 1, 1))
        self.assertEqual(totals["gpus"], 5)
        # cost_per_hour is per replica: 2 replicas of 2.5.
        self.assertEqual(totals["costPerHour"], "5.0")
        self.assertEqual(report["llmhosts"][0]["costPerHour"], "5.0")
        self.assertEqual(totals["estimatedCost"], "5.0")
        self.assertEqual(report["byEngine"], {"vllm": 1, "tgi": 1, "ollama": 1})
        self.assertEqual(report["llmhosts"][0]["gpus"], 4)
        self.assertIsNone(report["llmhosts"][0]["publicUrl"])

    def test_empty(self):
        self.assertEqual(build_report([])["totals"]["llmhosts"], 0)
