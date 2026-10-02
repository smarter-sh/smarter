"""Test the LLMHost service: :class:`smarter.apps.llmhost.services.LLMHostService`."""

from decimal import Decimal
from unittest.mock import MagicMock

from smarter.apps.account.models import Budget, Charge, ChargeTypes
from smarter.apps.llmhost.models import LLMHost, LLMHostEvent
from smarter.apps.llmhost.services import (
    HealthProber,
    LLMHostBudgetExceeded,
    LLMHostClusterError,
    LLMHostConfigurationError,
    LLMHostService,
)
from smarter.apps.llmhost.signals import (
    llmhost_destroyed,
    llmhost_launch_failed,
    llmhost_launched,
    llmhost_status_changed,
)
from smarter.apps.secret.models import Secret

from .base_classes import HF_TOKEN, LLMHostTestBase


def receive(signal):
    """Connect a mock receiver to a signal, and return it."""
    receiver = MagicMock()
    signal.connect(receiver, weak=False)
    return receiver


# pylint: disable=too-many-public-methods
class TestLLMHostService(LLMHostTestBase):
    """Test launch, observe, logs, destroy, delete, plan and report, on the in-memory cluster."""

    def setUp(self):
        super().setUp()
        self.service = LLMHostService(prober=HealthProber(enabled=False))

    def connect(self, signal):
        receiver = receive(signal)
        self.addCleanup(signal.disconnect, receiver)
        return receiver

    def kinds(self) -> list[str]:
        """The kinds of the LLMHost resources in the namespace: not the compute's Nodes."""
        return sorted(kind for kind, _ in self.cluster.resources if kind != "node")

    def events(self, llmhost: LLMHost) -> list[str]:
        return list(
            LLMHostEvent.objects.filter(llmhost=llmhost)
            .order_by("created_at", "id")
            .values_list("event_type", flat=True)
        )

    # --- discovery --------------------------------------------------------------------

    def test_discovery(self):
        """Test that discovery uses the catalogs."""
        models = self.service.search_models(query="qwen3", catalog="builtin")
        self.assertTrue(all("qwen3" in m.repository.lower() for m in models))
        self.assertEqual(self.service.get_model("qwen3_8b", catalog="builtin").repository, "Qwen/Qwen3-8B")
        self.assertEqual(
            self.service.draft_manifest("qwen3_8b", catalog="builtin", name="mine")["metadata"]["name"], "mine"
        )

    # --- launch -----------------------------------------------------------------------

    def test_plan(self):
        """Test that plan renders the resources with secrets redacted, and changes nothing."""
        llmhost = self.new_llmhost("test_service_plan")
        resources = self.service.plan(llmhost)
        secret = next(r for r in resources if r["kind"] == "Secret")
        self.assertEqual(set(secret["stringData"].values()), {"**redacted**"})
        self.assertEqual(self.cluster.resources, {})
        self.assertFalse(Secret.objects.filter(name="llmhost_test_service_plan_api_key").exists())

    def test_launch(self):
        """
        Test that launch applies the resources, with the token and a generated API key, adds a node to.

        its compute's node group, and records it.
        """
        launched = self.connect(llmhost_launched)
        llmhost = self.new_llmhost("test_service_launch")
        observation = self.service.launch(llmhost)
        base_name = self.base_name(llmhost)

        # the pods wait for the node that the node group is adding.
        self.assertEqual(observation.status, "provisioning")
        self.assertEqual(self.kinds(), ["deployment", "ingress", "persistentvolumeclaim", "secret", "service"])
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.compute.name, "gpu_a10g_1x")
        self.assertEqual(llmhost.status, "provisioning")
        self.assertEqual(self.nodegroups.created, [llmhost.compute.nodegroup_name])
        self.assertEqual(self.nodegroups.nodegroups[llmhost.compute.nodegroup_name].desired, 1)
        pod = self.cluster.get("deployment", base_name)["spec"]["template"]
        self.assertEqual(pod["metadata"]["labels"]["smarter.sh/compute"], "gpu_a10g_1x")
        self.assertEqual(pod["spec"]["nodeSelector"], {"smarter.sh/compute": "gpu_a10g_1x"})
        # once the node joins, the pods wait only for themselves.
        self.join_nodes(llmhost.compute)
        self.assertEqual(self.service.observe(llmhost).status, "pending")
        self.assertIsNotNone(llmhost.deployed_at)
        self.assertEqual(llmhost.endpoint_url, f"http://{base_name}.smarter-platform-test.svc.cluster.local/v1")
        self.assertTrue(llmhost.public_url.startswith(f"https://{base_name}.{self.account.account_number}."))
        self.assertEqual(llmhost.api_key_secret.name, "llmhost_test_service_launch_api_key")
        k8s_secret = self.cluster.get("secret", base_name)
        self.assertEqual(k8s_secret["stringData"]["HF_TOKEN"], HF_TOKEN)
        self.assertEqual(k8s_secret["stringData"]["API_KEY"], llmhost.api_key_secret.get_secret())
        self.assertGreaterEqual(len(k8s_secret["stringData"]["API_KEY"]), 32)
        self.assertEqual(self.events(llmhost), ["launched", "nodes_scaled", "status_changed"])
        launched.assert_called_once()
        self.assertIn(f"Deployment/{base_name}", launched.call_args.kwargs["resources"])

    def test_relaunch(self):
        """Test that launching again applies the changed spec, and keeps the API key and launch time."""
        llmhost = self.new_llmhost("test_service_relaunch")
        self.launch(llmhost)
        llmhost.refresh_from_db()
        api_key, deployed_at = llmhost.api_key_secret.get_secret(), llmhost.deployed_at
        llmhost.spec["scaling"] = {"replicas": 2}
        llmhost.spec["storage"] = {"accessMode": "ReadWriteMany"}
        llmhost.save()
        self.launch(llmhost)
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.api_key_secret.get_secret(), api_key)
        self.assertEqual(llmhost.deployed_at, deployed_at)
        self.assertEqual(llmhost.replicas, 2)
        self.assertEqual(self.cluster.get("deployment", self.base_name(llmhost))["spec"]["replicas"], 2)

    def test_launch_api_key_secret(self):
        """Test that network.apiKeySecret is used, rather than a generated key."""
        secret = self.create_secret("test_llmhost_my_api_key", "my-own-api-key")
        self.addCleanup(secret.delete)
        llmhost = self.new_llmhost("test_service_own_key", network={"apiKeySecret": "test_llmhost_my_api_key"})
        self.launch(llmhost)
        self.assertEqual(self.cluster.get("secret", self.base_name(llmhost))["stringData"]["API_KEY"], "my-own-api-key")
        self.assertFalse(Secret.objects.filter(name="llmhost_test_service_own_key_api_key").exists())

    def test_launch_without_secrets(self):
        """Test that an Ollama LLMHost, without a token or API key support, has no Secret, nor Ingress."""
        llmhost = self.new_llmhost("test_service_ollama", filename="llmhost-ollama.yaml")
        self.launch(llmhost)
        self.assertEqual(self.kinds(), ["deployment", "persistentvolumeclaim", "service"])
        llmhost.refresh_from_db()
        self.assertIsNone(llmhost.api_key_secret)
        self.assertEqual(llmhost.public_url, "")

    def test_launch_missing_token(self):
        """Test that a missing token Secret is a configuration error, and nothing is applied."""
        llmhost = self.new_llmhost("test_service_no_token", model={"tokenSecret": "test_llmhost_missing"})
        with self.assertRaisesRegex(LLMHostConfigurationError, "test_llmhost_missing"):
            self.service.launch(llmhost)
        self.assertEqual(self.cluster.applied, [])

    def test_launch_invalid_spec(self):
        """Test that an invalid stored spec is a configuration error."""
        llmhost = self.new_llmhost("test_service_invalid")
        LLMHost.objects.filter(pk=llmhost.pk).update(spec={"model": {"repository": "nope"}})
        llmhost.refresh_from_db()
        with self.assertRaises(LLMHostConfigurationError):
            self.service.launch(llmhost)

    def test_launch_cluster_unavailable(self):
        llmhost = self.new_llmhost("test_service_no_cluster")
        self.cluster.ready = False
        with self.assertRaises(LLMHostClusterError):
            self.service.launch(llmhost)

    def test_launch_budget_exceeded(self):
        """Test that an LLMHost is not launched when its compute's budget is exceeded."""
        failed = self.connect(llmhost_launch_failed)
        llmhost = self.new_llmhost("test_service_budget")
        budget = Budget.objects.create(
            name=f"test_service_budget_{self.hash_suffix}", periodic_limit=Decimal("1.00"), message="Over budget."
        )
        self.addCleanup(budget.delete)
        budget.attach(llmhost.compute)
        charge = Charge.objects.create(
            resource_locator=llmhost.compute.record_locator,  # type: ignore[union-attr]
            charge_type=ChargeTypes.COMPUTE.value,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            total_cost=Decimal("2.00"),
        )
        self.addCleanup(charge.delete)
        with self.assertRaisesRegex(LLMHostBudgetExceeded, "Over budget."):
            self.service.launch(llmhost)
        self.assertEqual(self.cluster.applied, [])
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status, "error")
        self.assertEqual(llmhost.status_message, "Over budget.")
        self.assertEqual(self.events(llmhost), ["error"])
        failed.assert_called_once()

    def test_launch_rejected(self):
        """Test that a rejected launch sets the error status, records it, and signals it."""
        failed = self.connect(llmhost_launch_failed)
        llmhost = self.new_llmhost("test_service_rejected")
        self.cluster.fail_apply = "quota exceeded"
        with self.assertRaisesRegex(LLMHostClusterError, "quota exceeded"):
            self.service.launch(llmhost)
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status, "error")
        self.assertIn("quota exceeded", llmhost.status_message)
        self.assertEqual(self.events(llmhost), ["error"])
        failed.assert_called_once()

    # --- observability ----------------------------------------------------------------

    def test_observe_lifecycle(self):
        """Test that status checks follow the LLMHost from provisioning to active, recording each change."""
        changed = self.connect(llmhost_status_changed)
        llmhost = self.new_llmhost("test_service_observe")
        self.launch(llmhost)
        self.assertEqual(self.service.observe(llmhost).status, "pending")
        self.simulate_pod(llmhost, ready=False)
        self.assertEqual(self.service.observe(llmhost).status, "deploying")
        self.simulate_ready(llmhost)
        observation = self.service.observe(llmhost)
        self.assertEqual((observation.status, observation.ready_replicas), ("active", 1))
        self.assertEqual(observation.pods[0]["ready"], True)
        self.assertIsNone(observation.healthy)
        llmhost.refresh_from_db()
        self.assertEqual((llmhost.status, llmhost.ready_replicas), ("active", 1))
        # provisioning -> pending -> deploying -> active.
        self.assertEqual(
            self.events(llmhost), ["launched", "nodes_scaled", "status_changed", "status_changed", "status_changed"]
        )
        self.assertEqual(changed.call_count, 3)
        self.assertEqual(changed.call_args.kwargs["new_status"], "active")
        # an unchanged status records nothing.
        self.service.observe(llmhost)
        self.assertEqual(len(self.events(llmhost)), 5)

    def test_observe_without_persist(self):
        llmhost = self.new_llmhost("test_service_no_persist")
        self.launch(llmhost)
        self.simulate_ready(llmhost)
        self.assertEqual(self.service.observe(llmhost, persist=False).status, "active")
        llmhost.refresh_from_db()
        self.assertEqual(llmhost.status, "provisioning")

    def test_observe_health(self):
        """Test that a failing health check degrades an active LLMHost, and a passing one is recorded."""
        prober = MagicMock(spec=HealthProber)
        service = LLMHostService(prober=prober)
        llmhost = self.new_llmhost("test_service_health")
        self.launch(llmhost, service)
        self.simulate_ready(llmhost)
        prober.check.return_value = False
        observation = service.observe(llmhost)
        self.assertEqual((observation.status, observation.healthy), ("degraded", False))
        self.assertIn("health check", observation.message)
        prober.check.return_value = True
        self.assertEqual(service.observe(llmhost).status, "active")
        llmhost.refresh_from_db()
        self.assertTrue(llmhost.last_health_ok)
        self.assertIsNotNone(llmhost.last_health_check_at)
        prober.check.assert_called_with(llmhost.health_check_url)

    def test_observe_resources_gone(self):
        """Test that an LLMHost whose resources were deleted outside Smarter becomes inactive."""
        llmhost = self.new_llmhost("test_service_gone")
        self.launch(llmhost)
        self.cluster.resources.clear()
        self.assertEqual(self.service.observe(llmhost).status, "inactive")

    def test_observe_cluster_unavailable(self):
        """Test that an unavailable cluster leaves the status unchanged."""
        llmhost = self.new_llmhost("test_service_observe_down")
        self.launch(llmhost)
        self.cluster.ready = False
        observation = self.service.observe(llmhost)
        self.assertEqual(observation.status, "provisioning")
        self.assertIn("not available", observation.message)

    def test_logs(self):
        """Test that logs returns the last lines, and that tail is clamped."""
        llmhost = self.new_llmhost("test_service_logs")
        self.cluster.pod_logs = "\n".join(f"INFO line {i}" for i in range(300))
        self.assertEqual(self.service.logs(llmhost, tail=2), "INFO line 298\nINFO line 299")
        self.assertEqual(len(self.service.logs(llmhost, tail=0).splitlines()), 1)
        self.cluster.ready = False
        with self.assertRaises(LLMHostClusterError):
            self.service.logs(llmhost)

    def test_report(self):
        llmhost = self.new_llmhost("test_service_report")
        self.launch(llmhost)
        report = self.service.report(LLMHost.objects.filter(pk=llmhost.pk))
        self.assertEqual(report["totals"]["deployed"], 1)
        self.assertEqual(report["totals"]["gpus"], 1)
        self.assertEqual(report["llmhosts"][0]["name"], "test_service_report")

    # --- destruction ------------------------------------------------------------------

    def test_destroy(self):
        """Test that destroy deletes the resources but keeps the model volume, and records it."""
        destroyed = self.connect(llmhost_destroyed)
        llmhost = self.new_llmhost("test_service_destroy")
        self.launch(llmhost)
        base_name = self.base_name(llmhost)
        self.cluster.apply([{"kind": "Secret", "metadata": {"name": f"{base_name}-tls"}}])
        self.service.destroy(llmhost)
        self.assertEqual(self.kinds(), ["persistentvolumeclaim"])
        # no other LLMHost needs its node, so it is removed.
        self.assertEqual(len(self.nodegroups.removed), 1)
        self.assertEqual(self.nodegroups.nodegroups[llmhost.compute.nodegroup_name].desired, 0)
        llmhost.refresh_from_db()
        self.assertEqual((llmhost.status, llmhost.ready_replicas), ("inactive", 0))
        self.assertIn("kept", llmhost.status_message)
        self.assertEqual(self.events(llmhost), ["launched", "nodes_scaled", "destroyed", "nodes_scaled"])
        event = LLMHostEvent.objects.get(llmhost=llmhost, event_type="destroyed")
        self.assertFalse(event.details["purge"])
        self.assertIsNotNone(event.details["uptimeHours"])
        destroyed.assert_called_once()
        # the API key Secret remains, for the next launch.
        self.assertIsNotNone(llmhost.api_key_secret)

    def test_destroy_purge(self):
        """Test that purge, and storage.retain false, also delete the model volume."""
        llmhost = self.new_llmhost("test_service_purge")
        self.launch(llmhost)
        self.service.destroy(llmhost, purge=True)
        self.assertEqual(self.kinds(), [])
        ollama = self.new_llmhost("test_service_no_retain", filename="llmhost-ollama.yaml")
        self.service.launch(ollama)
        self.service.destroy(ollama)
        self.assertEqual(self.kinds(), [])

    def test_destroy_cluster_unavailable(self):
        llmhost = self.new_llmhost("test_service_destroy_down")
        self.cluster.ready = False
        with self.assertRaises(LLMHostClusterError):
            self.service.destroy(llmhost)

    def test_delete(self):
        """Test that delete destroys everything, including the generated API key Secret, then the LLMHost."""
        llmhost = self.new_llmhost("test_service_delete")
        self.launch(llmhost)
        pk = llmhost.pk
        self.service.delete(llmhost)
        self.assertEqual(self.kinds(), [])
        self.assertFalse(LLMHost.objects.filter(pk=pk).exists())
        self.assertFalse(Secret.objects.filter(name="llmhost_test_service_delete_api_key").exists())
        self.assertTrue(Secret.objects.filter(pk=self.hf_secret.pk).exists())

    def test_delete_cluster_unavailable(self):
        """Test that a deployed LLMHost cannot be deleted without the cluster, but an undeployed one can."""
        llmhost = self.new_llmhost("test_service_delete_down")
        self.launch(llmhost)
        self.cluster.ready = False
        with self.assertRaises(LLMHostClusterError):
            self.service.delete(llmhost)
        undeployed = self.new_llmhost("test_service_delete_undeployed")
        self.service.delete(undeployed)
        self.assertFalse(LLMHost.objects.filter(pk=undeployed.pk).exists())
