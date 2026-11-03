"""Tests for smarter.apps.mcpserver.services.status.report: the platform's health, and what looks wrong in it."""

from datetime import datetime, timezone
from unittest import mock

from smarter.apps.infrastructure.cluster_health import ClusterHealth
from smarter.apps.mcpserver.services.status.feeds import ProviderStatus
from smarter.apps.mcpserver.services.status.platform import DatabaseLoad
from smarter.apps.mcpserver.services.status.report import (
    QUEUE_BACKLOG,
    EksStatus,
    PlatformStatus,
    eks_status,
    platform_status,
    service_observations,
    upstream_observations,
    utc,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .test_tools_status import EVENT, TOOLS, StatusToolsTestBase


class TestPlatformStatus(StatusToolsTestBase):
    """Test platform_status, with the in-memory cluster and the faked services and status pages."""

    def test_report(self):
        """Everything that was read is in the report, with what looks wrong."""
        status = platform_status(60)
        self.assertIsInstance(status, PlatformStatus)
        self.assertEqual(status.checks, self.checks)
        self.assertEqual(status.database, self.database)
        self.assertTrue(status.snapshot.pods)
        self.assertIn(
            "Pod smarter-worker-5b8d4c-x9y8z (smarter-worker) is not healthy: CrashLoopBackOff.", status.observations
        )
        self.assertIn("1 Kubernetes warning events in the period.", status.observations)

    def test_database_down(self):
        """A database that cannot be read is None, and an observation."""
        with mock.patch(f"{TOOLS}.database_load", side_effect=RuntimeError("gone away")):
            status = platform_status(60)
        self.assertIsNone(status.database)
        self.assertIn("The database's load could not be read.", status.observations)


class TestEksStatus(StatusToolsTestBase):
    """Test eks_status, with the in-memory cloud provider."""

    def test_report(self):
        """The cluster's health comes from the provider, with the region's AWS events."""
        self.provider.cluster_health = ClusterHealth(name="cluster", status="ACTIVE", version="1.33")
        self.aws_events = [EVENT]
        status = eks_status()
        self.assertIsInstance(status, EksStatus)
        self.assertEqual(status.health.name, "cluster")
        self.assertEqual(status.aws_events, [EVENT])


class TestObservations(SmarterTestBase):
    """Test the observations of the backing services and the upstream status pages, which need no cluster."""

    def test_service_observations(self):
        """A failed check, a backlog, an unread queue and a busy database are observations."""
        checks = [("Cache", True), ("Workers", False)]
        depths = {"default": QUEUE_BACKLOG, "other": None, "quiet": 0}
        database = DatabaseLoad(connections=140, max_connections=150)
        found = service_observations(checks, depths, database)
        self.assertEqual(
            found,
            [
                "The Workers health check failed.",
                f"{QUEUE_BACKLOG} tasks are waiting in the Celery queue default: the workers are behind.",
                "The Celery queue other could not be read.",
                "The database has 140 of 150 connections in use.",
            ],
        )
        self.assertEqual(service_observations([], {}, DatabaseLoad(connections=1, max_connections=150)), [])

    def test_upstream_observations(self):
        """A provider in trouble is an observation, and one whose page could not be read is not."""
        providers = [
            ProviderStatus(
                name="OpenAI", url="https://status.openai.com/", indicator="major", description="Major Outage"
            ),
            ProviderStatus(name="Mistral", url="https://status.mistral.ai/"),
        ]
        found = upstream_observations(providers, [EVENT])
        self.assertEqual(len(found), 2)
        self.assertIn("OpenAI reports Major Outage", found[0])
        self.assertIn("AWS EKS event: Increased API error rates", found[1])

    def test_utc(self):
        """A time is shown in UTC, and an unknown one as a question mark."""
        self.assertEqual(utc(None), "?")
        self.assertEqual(utc(datetime(2026, 11, 2, 14, 5, tzinfo=timezone.utc)), "2026-11-02 14:05:00 UTC")
