"""
Tests of smarter.apps.llmclient.tasks.retarget_ingresses, and its command, retarget_llmclient_ingresses.

The Kubernetes service and apply_ingress_manifest() are replaced with mocks: the local containers' kubeconfig is
a real cluster's, so nothing here may reach it.
"""

import io
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import retarget_ingresses
from smarter.apps.llmclient.tasks.utils import API_SERVICE_NAME, LEGACY_API_SERVICE_NAME

MODULE = "smarter.apps.llmclient.tasks.retarget_ingresses"


def ingress(service_name: str) -> dict:
    """An ingress, as the Kubernetes api returns it, that sends its requests to a Service."""
    backend = {"service": {"name": service_name, "port": {"number": 8000}}}
    return {"spec": {"rules": [{"http": {"paths": [{"backend": backend, "path": "/"}]}}]}}


class TestRetargetIngresses(TestAccountMixin):
    """Only deployed LLMClients' ingresses that still name the old Service are rewritten."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_retarget_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        # update(), not save(), so that no deployment signal runs.
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=True)
        self.llmclient.refresh_from_db()
        self.host = self.llmclient.default_host

        self.kubernetes = MagicMock()
        self.kubernetes.ready = True
        infrastructure = MagicMock(kubernetes=self.kubernetes)
        patcher = patch(f"{MODULE}.infrastructure", infrastructure)
        patcher.start()
        self.addCleanup(patcher.stop)
        apply_patcher = patch(f"{MODULE}.apply_ingress_manifest")
        self.apply_ingress_manifest = apply_patcher.start()
        self.addCleanup(apply_patcher.stop)
        settings = retarget_ingresses.smarter_settings.model_copy(
            update={"llmclient_tasks_create_ingress_manifest": True}
        )
        settings_patcher = patch(f"{MODULE}.smarter_settings", settings)
        settings_patcher.start()
        self.addCleanup(settings_patcher.stop)

    def ingresses(self, by_host: dict):
        """The cluster has these ingresses, by host, and no others."""
        self.kubernetes.get_resource.side_effect = lambda kind, name, namespace: by_host.get(name)

    def test_service_names(self):
        self.assertEqual(API_SERVICE_NAME, "smarter-api")
        self.assertEqual(LEGACY_API_SERVICE_NAME, "smarter")

    def test_deployed_hosts(self):
        """A deployed LLMClient's default host is listed; an undeployed one's isn't."""
        self.assertIn(self.host, retarget_ingresses.deployed_hosts())
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=False)
        self.assertNotIn(self.host, retarget_ingresses.deployed_hosts())

    def test_rewrites_an_ingress_that_names_the_old_service(self):
        self.ingresses({self.host: ingress(LEGACY_API_SERVICE_NAME)})
        hosts = retarget_ingresses.retarget_llmclient_ingresses()
        self.assertEqual(hosts, [self.host])
        self.apply_ingress_manifest.assert_called_once_with(self.host)

    def test_leaves_retargeted_and_missing_ingresses_alone(self):
        """An ingress that names the new Service, or no ingress at all, is left alone."""
        self.ingresses({self.host: ingress(API_SERVICE_NAME)})
        self.assertEqual(retarget_ingresses.retarget_llmclient_ingresses(), [])
        self.ingresses({})
        self.assertEqual(retarget_ingresses.retarget_llmclient_ingresses(), [])
        self.apply_ingress_manifest.assert_not_called()

    def test_dry_run_changes_nothing(self):
        self.ingresses({self.host: ingress(LEGACY_API_SERVICE_NAME)})
        self.assertEqual(retarget_ingresses.retarget_llmclient_ingresses(dry_run=True), [self.host])
        self.apply_ingress_manifest.assert_not_called()

    def test_skips_without_kubernetes_or_ingresses(self):
        """Without Kubernetes, or on a platform that creates no ingresses, nothing is read or written."""
        self.kubernetes.ready = False
        self.assertEqual(retarget_ingresses.retarget_llmclient_ingresses(), [])
        self.kubernetes.ready = True
        settings = retarget_ingresses.smarter_settings.model_copy(
            update={"llmclient_tasks_create_ingress_manifest": False}
        )
        with patch(f"{MODULE}.smarter_settings", settings):
            self.assertEqual(retarget_ingresses.retarget_llmclient_ingresses(), [])
        self.kubernetes.get_resource.assert_not_called()

    def test_backend_service_name_of_an_unusual_ingress(self):
        self.assertIsNone(retarget_ingresses.backend_service_name({}))
        self.assertIsNone(retarget_ingresses.backend_service_name({"spec": {"rules": [{"http": {}}]}}))
        self.assertEqual(retarget_ingresses.backend_service_name(ingress("x")), "x")

    def test_command(self):
        """The command prints each host, and the total; --dry-run says what it would do."""
        self.ingresses({self.host: ingress(LEGACY_API_SERVICE_NAME)})
        output = io.StringIO()
        call_command("retarget_llmclient_ingresses", "--dry-run", stdout=output)
        self.assertIn(f"Would retarget the ingress of {self.host}", output.getvalue())
        self.apply_ingress_manifest.assert_not_called()
        output = io.StringIO()
        call_command("retarget_llmclient_ingresses", stdout=output)
        self.assertIn(f"Retargeted the ingress of {self.host}", output.getvalue())
        self.apply_ingress_manifest.assert_called_once_with(self.host)
