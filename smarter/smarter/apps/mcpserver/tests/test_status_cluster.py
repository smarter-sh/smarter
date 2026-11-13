"""Test smarter.apps.mcpserver.services.status.cluster, with the in-memory test cluster."""

from datetime import datetime, timezone

from smarter.apps.mcpserver.services.status.cluster import (
    cluster_snapshot,
    mebibytes,
    parse_cpu,
    parse_memory,
    parse_time,
    percent,
    pod_status,
    warning_event,
)
from smarter.common.conf import smarter_settings
from smarter.lib.typing import required

from .operations_base import OperationsTestBase


class TestQuantities(OperationsTestBase):
    """Test the conversions of Kubernetes quantities, percentages and times."""

    def test_parse_cpu(self):
        self.assertEqual(parse_cpu("250m"), 0.25)
        self.assertEqual(parse_cpu("2"), 2.0)
        self.assertAlmostEqual(required(parse_cpu("350000000n"), "parse_cpu"), 0.35)
        self.assertAlmostEqual(required(parse_cpu("500u"), "parse_cpu"), 0.0005)
        self.assertIsNone(parse_cpu("1Gi"), "a memory quantity is not CPU")
        self.assertIsNone(parse_cpu(None))
        self.assertIsNone(parse_cpu("lots"))

    def test_parse_memory(self):
        self.assertEqual(parse_memory("1280Mi"), 1280 * 1024**2)
        self.assertEqual(parse_memory("2Gi"), 2 * 1024**3)
        self.assertEqual(parse_memory("1G"), 1000**3)
        self.assertEqual(parse_memory("512"), 512)
        self.assertIsNone(parse_memory("250m"), "a CPU quantity is not memory")
        self.assertIsNone(parse_memory(""))

    def test_mebibytes_and_percent(self):
        self.assertEqual(mebibytes(512 * 1024**2), "512Mi")
        self.assertEqual(mebibytes(None), "?")
        self.assertEqual(percent(50, 200), 25)
        self.assertIsNone(percent(None, 200))
        self.assertIsNone(percent(50, None))
        self.assertIsNone(percent(50, 0))

    def test_parse_time(self):
        self.assertEqual(parse_time("2026-11-02T14:00:00Z"), datetime(2026, 11, 2, 14, tzinfo=timezone.utc))
        self.assertIsNotNone(parse_time("2026-11-02T14:00:00.123456Z"))
        self.assertIsNone(parse_time("yesterday"))
        self.assertIsNone(parse_time(None))


class TestClusterSnapshot(OperationsTestBase):
    """Test cluster_snapshot()."""

    def snapshot(self):
        return cluster_snapshot(smarter_settings.environment_namespace)

    def test_pods(self):
        snapshot = self.snapshot()
        pods = {pod.component: pod for pod in snapshot.pods}
        self.assertNotIn("smarter-mysql-backup-29000000", pods, "a finished Job's pod is left out")
        app = pods["smarter"]
        self.assertTrue(app.ready)
        self.assertEqual(app.problem, "")
        self.assertAlmostEqual(app.cpu, 0.35)
        self.assertEqual(app.memory_limit, 2 * 1024**3)
        self.assertEqual(app.cpu_request, 1.0)
        worker = pods["smarter-worker"]
        self.assertFalse(worker.ready)
        self.assertEqual(worker.problem, "CrashLoopBackOff", "the current state comes before the last one")
        self.assertEqual(worker.restarts, 7)
        self.assertIsNone(worker.cpu, "metrics-server does not report a pod that is not running")
        beat = pods["smarter-beat"]
        self.assertTrue(beat.ready)
        self.assertEqual(beat.problem, "last restart: OOMKilled")
        self.assertEqual([pod.component for pod in snapshot.pods], ["smarter", "smarter-beat", "smarter-worker"])

    def test_nodes(self):
        nodes = self.snapshot().nodes
        first, second = nodes
        self.assertTrue(first.ready)
        self.assertEqual(first.capacity_type, "SPOT")
        self.assertEqual(first.instance_type, "t3.xlarge")
        self.assertEqual(percent(first.cpu, first.cpu_allocatable), 50)
        self.assertEqual(second.pressures, ["MemoryPressure"])
        self.assertTrue(second.unschedulable)

    def test_events(self):
        events = self.snapshot().events
        self.assertEqual(len(events), 1, "only warnings")
        event = events[0]
        self.assertEqual(event.object, "pod/smarter-worker-5b8d4c-x9y8z")
        self.assertEqual(event.reason, "BackOff")
        self.assertEqual(event.count, 12)
        self.assertEqual(cluster_snapshot(smarter_settings.environment_namespace, minutes=1).events, [], "too old")

    def test_unreadable_parts(self):
        """A part that cannot be read is named, and the others are still read."""
        del self.cluster.items["pods.metrics.k8s.io"]
        del self.cluster.items["node"]
        del self.cluster.items["event"]
        snapshot = self.snapshot()
        self.assertEqual(len(snapshot.pods), 3)
        self.assertIsNone(snapshot.pods[0].cpu)
        self.assertEqual(snapshot.nodes, [])
        self.assertEqual(
            snapshot.errors,
            [
                "pod metrics: metrics-server could not be read",
                "nodes: the cluster could not be read",
                "events: the cluster could not be read",
            ],
        )
        del self.cluster.items["pod"]
        del self.cluster.items["nodes.metrics.k8s.io"]
        self.cluster.items["node"] = []
        errors = self.snapshot().errors
        self.assertIn("pods: the cluster could not be read", errors)
        self.assertIn("node metrics: metrics-server could not be read", errors)


class TestResourceParsing(OperationsTestBase):
    """Test pod_status() and warning_event() on the forms that the test cluster does not have."""

    def test_pending_pod(self):
        pod = {
            "metadata": {"name": "p", "labels": {"app": "third-party"}},
            "status": {"phase": "Pending", "reason": "Unschedulable"},
        }
        status = pod_status(pod)
        self.assertEqual(status.problem, "Unschedulable")
        self.assertEqual(status.component, "third-party")
        self.assertFalse(status.ready, "a pod without containers is not ready")
        self.assertEqual(pod_status({"metadata": {"name": "bare"}, "status": {"phase": "Pending"}}).component, "bare")

    def test_terminated_container(self):
        pod = {"status": {"containerStatuses": [{"state": {"terminated": {"reason": "Error"}}}]}}
        self.assertEqual(pod_status(pod).problem, "Error")

    def test_event_times(self):
        """An event's last time comes from its series, its lastTimestamp, its eventTime, or its creation."""
        series = warning_event({"series": {"lastObservedTime": "2026-11-02T14:00:00Z", "count": 3}})
        self.assertEqual((required(series.last_seen, "series.last_seen").hour, series.count), (14, 3))
        new = warning_event({"eventTime": "2026-11-02T13:00:00.000000Z"})
        self.assertEqual(required(new.last_seen, "new.last_seen").hour, 13)
        created = warning_event({"metadata": {"creationTimestamp": "2026-11-02T12:00:00Z"}})
        self.assertEqual(required(created.last_seen, "created.last_seen").hour, 12)
        self.assertIsNone(warning_event({}).last_seen)
