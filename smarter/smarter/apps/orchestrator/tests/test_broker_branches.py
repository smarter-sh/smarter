"""Test SAMOrchestratorBroker's not-found, not-ready and failure branches."""

from unittest.mock import MagicMock

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator.manifest.brokers.orchestrator import (
    SAMOrchestratorBroker,
    SAMOrchestratorBrokerError,
)
from smarter.apps.orchestrator.manifest.models.orchestrator.spec import (
    SAMOrchestratorHarnessConfig,
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

    # -------------------------------------------------------------------------
    # harnesses in the owner's account tree, or in another account (ADR-037)
    # -------------------------------------------------------------------------
    def new_llmclient(self, user_profile, role: str) -> LLMClient:
        """An LLMClient of the profile, deleted after the test."""
        llmclient = LLMClient.objects.create(name=f"test_harness_{role}_{self.hash_suffix}", user_profile=user_profile)
        self.addCleanup(llmclient.delete)
        return llmclient

    def as_owner(self, user_profile) -> SAMOrchestratorBroker:
        """The broker, applying as the profile, in its account."""
        self.patch_property("user", user_profile.user)
        self.patch_property("user_profile", user_profile)
        self.patch_property("account", user_profile.account)
        return self.broker

    def test_harness_of_the_owners_account(self):
        """A harness without accountNumber names an LLMClient of the owner's account, and describes without one."""
        llmclient = self.new_llmclient(self.user_profile, "own")
        broker = self.as_owner(self.user_profile)
        harness = SAMOrchestratorHarnessConfig(llmClientName=llmclient.name)
        self.assertEqual(broker.resolve_harness_llmclient(harness), llmclient)
        self.assertIsNone(broker.harness_account_number(MagicMock(llmclient=llmclient)))
        with self.assertRaises(SAMOrchestratorBrokerError):
            broker.resolve_harness_llmclient(SAMOrchestratorHarnessConfig(llmClientName="no_such_llmclient"))

    def test_harness_of_another_account(self):
        """A harness may name another account's LLMClient, which the owner may read as a member of that account."""
        _, department, department_profile = mortal_user_factory()
        self.addCleanup(department.delete)
        llmclient = self.new_llmclient(department_profile, "department")
        harness = SAMOrchestratorHarnessConfig(llmClientName=llmclient.name, accountNumber=department.account_number)
        broker = self.as_owner(self.non_admin_user_profile)
        # not a member of the department: refused, as if it didn't exist.
        with self.assertRaisesRegex(SAMOrchestratorBrokerError, "or you may not read it"):
            broker.resolve_harness_llmclient(harness)

        membership = UserProfile.objects.create(
            user=self.non_admin_user, account=department, name=f"test_harness_member_{self.hash_suffix}"
        )
        self.addCleanup(UserProfile.objects.filter(pk=membership.pk).delete)
        self.assertEqual(broker.resolve_harness_llmclient(harness), llmclient)
        self.assertEqual(broker.harness_account_number(MagicMock(llmclient=llmclient)), department.account_number)
