"""Test smarter.apps.mcpserver.protocol.tools.status: platform_status and eks_status, with the in-memory cluster and provider."""

from datetime import datetime, timezone
from typing import Optional
from unittest import mock

from smarter.apps.infrastructure.cluster_health import (
    AddonHealth,
    ClusterHealth,
    ClusterInsight,
    HealthIssue,
    NodeGroupHealth,
)
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.protocol.tools.staff import UNTRUSTED_DATA_NOTICE
from smarter.apps.mcpserver.protocol.tools.status import (
    EksStatusTool,
    PlatformStatusTool,
)
from smarter.apps.mcpserver.services.status.feeds import AwsEvent, ProviderStatus
from smarter.apps.mcpserver.services.status.platform import (
    DatabaseLoad,
    HealthCheckResult,
)
from smarter.common.conf import smarter_settings

from .operations_base import TICKET, OperationsTestBase

TOOLS = "smarter.apps.mcpserver.services.status.report"
DEFAULT_QUEUE = smarter_settings.llmclient_tasks_celery_task_queue
INFRASTRUCTURE_QUEUE = smarter_settings.infrastructure_tasks_celery_task_queue
EVENT = AwsEvent(
    service="EKS",
    published=datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc),
    title="Increased API error rates",
    description="details",
)


class StatusToolsTestBase(OperationsTestBase):
    """Fake the backing services and the status feeds, which the in-memory fakes do not cover."""

    def setUp(self):
        super().setUp()
        self.checks = [
            HealthCheckResult("Database", True),
            HealthCheckResult("Cache", True),
            HealthCheckResult("Task Broker", True),
            HealthCheckResult("Workers", True),
        ]
        self.depths: dict[str, Optional[int]] = {DEFAULT_QUEUE: 0, INFRASTRUCTURE_QUEUE: 0}
        self.database = DatabaseLoad(connections=10, max_connections=150, running=1, slow_queries=0)
        self.providers = [
            ProviderStatus(
                name="OpenAI", url="https://status.openai.com/", indicator="none", description="All Systems Operational"
            ),
            ProviderStatus(name="Mistral", url="https://status.mistral.ai/"),
        ]
        self.aws_events: list[AwsEvent] = []
        self.unread_feeds: list[str] = []
        fakes = {
            "health_checks": lambda: self.checks,
            "queue_depths": lambda: self.depths,
            "database_load": lambda: self.database,
            "provider_statuses": lambda: self.providers,
            "aws_service_events": lambda region: (self.aws_events, self.unread_feeds),
        }
        for name, fake in fakes.items():
            patcher = mock.patch(f"{TOOLS}.{name}", side_effect=fake)
            patcher.start()
            self.addCleanup(patcher.stop)


class TestPlatformStatusTool(StatusToolsTestBase):
    """Test platform_status."""

    def status(self, **arguments) -> str:
        return PlatformStatusTool(self.admin_user).call({"ticket": TICKET, **arguments})

    def test_report(self):
        text = self.status()
        self.assertTrue(text.startswith(UNTRUSTED_DATA_NOTICE))
        observations = text.split("### Pods")[0]
        self.assertIn("smarter-worker-5b8d4c-x9y8z (smarter-worker) is not healthy: CrashLoopBackOff", observations)
        self.assertIn("smarter-beat-7c6d5e-q1w2e (smarter-beat) is not healthy: last restart: OOMKilled", observations)
        self.assertIn("smarter-beat-7c6d5e-q1w2e uses 96% of its memory limit", observations)
        self.assertIn("Node ip-10-0-0-2.ec2.internal reports MemoryPressure.", observations)
        self.assertIn("Node ip-10-0-0-2.ec2.internal is cordoned", observations)
        self.assertIn("Node ip-10-0-0-2.ec2.internal uses 97% of its CPU.", observations)
        self.assertIn("Node ip-10-0-0-2.ec2.internal uses 93% of its memory.", observations)
        self.assertIn("1 Kubernetes warning events in the period.", observations)
        self.assertNotIn("Mistral", observations, "a provider whose status is unknown is not an observation")
        self.assertIn("| smarter | smarter-6f9c7d-a1b2c | 1/1 | 0 |  | 0.35 | 900Mi (44%) |", text)
        self.assertIn("| ip-10-0-0-1.ec2.internal | yes | t3.xlarge spot | 50% | 50% |  |", text)
        self.assertIn("pod/smarter-worker-5b8d4c-x9y8z BackOff (×12): Back-off restarting failed container", text)
        self.assertIn("- Workers: healthy", text)
        self.assertIn(f"- Celery queue {DEFAULT_QUEUE}: 0 waiting", text)
        self.assertIn("- Database: 10 of 150 connections, 1 running, 0 slow queries", text)
        self.assertIn("- OpenAI: All Systems Operational (https://status.openai.com/)", text)
        self.assertIn("no events in the last 3 days", text)
        self.assertEqual(self.audit_rows().first().tool, "platform_status")

    def test_services_and_upstream(self):
        self.checks[3] = HealthCheckResult("Workers", False, "TimeoutError: no worker answered")
        self.depths = {DEFAULT_QUEUE: 120, INFRASTRUCTURE_QUEUE: None}
        self.database = DatabaseLoad(connections=140, max_connections=150)
        self.providers[0] = ProviderStatus(
            name="OpenAI", url="https://status.openai.com/", indicator="major", description="Major Outage"
        )
        self.aws_events = [EVENT]
        self.unread_feeds = ["EC2"]
        text = self.status()
        self.assertIn("The Workers health check failed: TimeoutError: no worker answered.", text)
        self.assertIn(f"120 tasks are waiting in the Celery queue {DEFAULT_QUEUE}", text)
        self.assertIn(f"The Celery queue {INFRASTRUCTURE_QUEUE} could not be read.", text)
        self.assertIn("The database has 140 of 150 connections in use.", text)
        self.assertIn("OpenAI reports Major Outage", text)
        self.assertIn("AWS EKS event: Increased API error rates (2026-11-02 20:00:00 UTC).", text)
        self.assertIn("- AWS EC2: could not be read", text)
        self.assertIn("- Workers: FAILED, TimeoutError: no worker answered", text)
        self.assertIn(f"- Celery queue {INFRASTRUCTURE_QUEUE}: unknown", text)

    def test_database_down(self):
        with mock.patch(f"{TOOLS}.database_load", side_effect=RuntimeError("gone away")):
            text = self.status()
        self.assertIn("The database's load could not be read.", text)
        self.assertIn("- Database: its load could not be read", text)

    def test_healthy_and_unreadable_cluster(self):
        """With no pods, nodes or events to report, the parts that could not be read are observations."""
        self.cluster.items = {"node": [], "nodes.metrics.k8s.io": []}
        text = self.status()
        self.assertIn("Could not read pods: the cluster could not be read.", text)
        self.assertIn("### Kubernetes warning events in the last 60 minutes\n\n- None.", text.replace("\r", ""))

    def test_nothing_wrong(self):
        self.cluster.items = {"pod": [], "pods.metrics.k8s.io": [], "node": [], "nodes.metrics.k8s.io": [], "event": []}
        self.assertIn("- Nothing looks wrong.", self.status())

    def test_minutes(self):
        """The period of warning events is at least 5 minutes, and an older event is left out."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "minutes"):
            self.status(minutes=1)
        text = self.status(minutes=5)
        self.assertIn("### Kubernetes warning events in the last 5 minutes\n\n- None.", text)


class TestEksStatusTool(StatusToolsTestBase):
    """Test eks_status."""

    def eks_status(self) -> str:
        return EksStatusTool(self.admin_user).call({"ticket": TICKET})

    def test_report(self):
        self.provider.cluster_health = ClusterHealth(
            name="cluster",
            status="ACTIVE",
            version="1.33",
            platform_version="eks.9",
            nodegroups=[
                NodeGroupHealth(
                    name="default",
                    status="DEGRADED",
                    desired_size=3,
                    min_size=3,
                    max_size=15,
                    instance_types=("t3.xlarge",),
                    capacity_type="SPOT",
                    issues=(HealthIssue(code="AsgInstanceLaunchFailures", message="no capacity", resources=("i-1",)),),
                )
            ],
            addons=[
                AddonHealth(name="coredns", version="v1.9.0", status="ACTIVE", latest_version="v1.11.0"),
                AddonHealth(
                    name="vpc-cni",
                    version="v1.19.0",
                    status="DEGRADED",
                    issues=(HealthIssue(code="InsufficientNumberOfReplicas"),),
                ),
            ],
            insights=[
                ClusterInsight(
                    name="Deprecated APIs",
                    category="UPGRADE_READINESS",
                    status="WARNING",
                    reason="in use",
                    kubernetes_version="1.34",
                ),
                ClusterInsight(name="Kubelet skew", category="UPGRADE_READINESS", status="PASSING"),
            ],
            errors=["insights: AccessDeniedException"],
        )
        self.aws_events = [EVENT]
        self.unread_feeds = ["EC2"]
        text = self.eks_status()
        self.assertIn("- Control plane: ACTIVE, Kubernetes 1.33, platform version eks.9", text)
        self.assertIn("- No control plane health issues.", text)
        self.assertIn("- default: DEGRADED, 3 nodes (min 3, max 15), t3.xlarge spot, image ?", text)
        self.assertIn("  - issue AsgInstanceLaunchFailures: no capacity (1 resources)", text)
        self.assertIn("- coredns v1.9.0: ACTIVE, update available: v1.11.0", text)
        self.assertIn("- vpc-cni v1.19.0: DEGRADED\n  - issue InsufficientNumberOfReplicas: ", text)
        self.assertIn("- WARNING UPGRADE_READINESS Deprecated APIs (Kubernetes 1.34): in use", text)
        self.assertIn("- 1 insights are passing.", text)
        self.assertIn("- Could not read insights: AccessDeniedException.", text)
        self.assertIn("2026-11-02 20:00:00 UTC EKS: Increased API error rates", text)
        self.assertIn("- AWS EC2: the status feed could not be read", text)

    def test_from_cluster_info(self):
        """A provider without node groups, add-ons or insights reports what it knows."""
        self.provider.cluster_info["health"] = {"issues": [{"code": "IamRoleNotFound", "message": "role"}]}
        text = self.eks_status()
        self.assertIn("- Control plane issue IamRoleNotFound: role", text)
        self.assertEqual(text.count("- None listed."), 3)
        self.assertIn("### AWS events in", text)
        self.assertTrue(text.rstrip().endswith("- None."))

    def test_provider_not_ready(self):
        self.provider.ready = False
        with self.assertRaisesRegex(SmarterMCPServerToolError, "eks_status is not available on this platform"):
            self.eks_status()
        self.assertTrue(self.audit_rows().first().is_error)
