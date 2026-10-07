"""Test SAMOrchestratorBroker's not-found, not-ready and failure branches."""

from unittest.mock import MagicMock

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.orchestrator.manifest.brokers.orchestrator import (
    SAMOrchestratorBroker,
    SAMOrchestratorBrokerError,
)
from smarter.apps.orchestrator.models import Orchestrator
from smarter.lib.manifest.broker import SAMBrokerErrorNotReady
from smarter.lib.unittest.broker_branches import BrokerBranchesTestMixin, api_test_data


class TestOrchestratorBrokerBranches(BrokerBranchesTestMixin, TestAccountMixin):
    """Test the SAMOrchestratorBroker branches that the cli broker tests don't reach."""

    broker_class = SAMOrchestratorBroker
    error_class = SAMOrchestratorBrokerError
    resource_property = "orchestrator"
    model = Orchestrator
    manifest_path = api_test_data("orchestrator", "orchestrator.yaml")

    def test_sync_harnesses_needs_a_manifest(self):
        """Sync_harnesses isn't ready without a manifest."""
        self.patch_property("manifest", None)
        with self.assertRaises(SAMBrokerErrorNotReady):
            self.broker.sync_harnesses()

    def test_sync_harnesses_needs_a_saved_orchestrator(self):
        """Sync_harnesses needs an Orchestrator that has been saved."""
        self.patch_property("orchestrator", MagicMock(spec=Orchestrator, pk=None))
        with self.assertRaises(SAMOrchestratorBrokerError):
            self.broker.sync_harnesses()

    def test_sync_harnesses_needs_the_llmclients(self):
        """Sync_harnesses raises when a harness names an LLMClient that doesn't exist."""
        self.patch_property("orchestrator", MagicMock(spec=Orchestrator, pk=1))
        with self.assertRaises(SAMOrchestratorBrokerError):
            self.broker.sync_harnesses()
