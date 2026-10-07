"""
Test the Orchestrator manifest broker through the api/v1/cli/ commands.

See :class:`smarter.lib.unittest.cli_brokers.CliBrokerTestMixin`.
"""

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator.models import Orchestrator
from smarter.lib.unittest.cli_brokers import CliBrokerTestMixin


class TestOrchestratorBroker(CliBrokerTestMixin, ApiV1TestBase):
    """Test the Orchestrator broker."""

    kind = SAMKinds.ORCHESTRATOR.value
    model = Orchestrator
    name_prefix = "test_orchestrator_broker"

    def setUp(self):
        super().setUp()
        # the LLMClients that the example manifest's planner and executor harnesses name.
        self.llmclients = []
        for role in ("planner", "executor"):
            llmclient = LLMClient.objects.create(
                name=f"test_orchestrator_{role}_{self.hash_suffix}", user_profile=self.user_profile
            )
            self.addCleanup(llmclient.delete)
            self.llmclients.append(llmclient)

    def prepare_manifest(self, manifest):
        manifest = super().prepare_manifest(manifest)
        for harness, llmclient in zip(manifest["spec"]["config"]["harnesses"], self.llmclients):
            harness["llmClientName"] = llmclient.name
        return manifest

    def test_get(self):
        super().test_get()

    def test_apply_describe(self):
        self.apply()
        response = self.cli("describe", name=self.name)
        self.assertEqual(response["data"]["metadata"]["name"], self.name)

    def test_apply_describe_delete(self):
        super().test_apply_describe_delete()
