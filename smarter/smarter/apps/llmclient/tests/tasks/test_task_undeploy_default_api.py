"""
Test :mod:`smarter.apps.llmclient.tasks.undeploy_default_api`.

The task is called directly, which runs it synchronously, in this process. AWS is
mocked: no Route53 record is read or destroyed.
"""

import threading
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

from django.db import connection

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import deploy_default_api, undeploy_default_api
from smarter.common.conf import smarter_settings

MODULE = "smarter.apps.llmclient.tasks.undeploy_default_api"
DEPLOY_MODULE = "smarter.apps.llmclient.tasks.deploy_default_api"


class TestUndeployDefaultApi(TestAccountMixin):
    """Test that undeploying an LLMClient destroys its default domain A record, and resets its state."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_undeploy_default_api_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        # the task is queued when an llmclient that was deployed is saved as not deployed.
        # update(), rather than save(), which would queue a real undeployment.
        LLMClient.objects.filter(pk=self.llmclient.pk).update(
            deployed=False, dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFIED
        )
        patcher = patch(f"{MODULE}.is_taskable", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_undeploy(self):
        """Test that the default domain's A record is destroyed, and the llmclient is no longer deployed."""
        with patch(f"{MODULE}.destroy_domain_A_record") as destroy_domain_A_record:
            undeploy_default_api(llmclient_id=self.llmclient.pk)

        destroy_domain_A_record.assert_called_once()
        kwargs = destroy_domain_A_record.call_args.kwargs
        self.assertEqual(kwargs["hostname"], urlparse(self.llmclient.default_url).netloc)
        self.assertEqual(kwargs["api_host_domain"], smarter_settings.environment_api_domain)

        llmclient = LLMClient.objects.get(pk=self.llmclient.pk)
        self.assertFalse(llmclient.deployed)
        self.assertEqual(llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED)

    def test_deployed_again(self):
        """Test that an llmclient that was deployed again since the task was queued keeps its A record."""
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=True)
        with patch(f"{MODULE}.destroy_domain_A_record") as destroy_domain_A_record:
            self.assertIsNone(undeploy_default_api(llmclient_id=self.llmclient.pk))
        destroy_domain_A_record.assert_not_called()
        llmclient = LLMClient.objects.get(pk=self.llmclient.pk)
        self.assertTrue(llmclient.deployed)
        self.assertEqual(llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.VERIFIED)

    def test_unknown_llmclient(self):
        """Test that undeploying an llmclient that does not exist destroys nothing."""
        with patch(f"{MODULE}.destroy_domain_A_record") as destroy_domain_A_record:
            self.assertIsNone(undeploy_default_api(llmclient_id=999999999))
        destroy_domain_A_record.assert_not_called()

    def test_not_taskable(self):
        """Test that nothing is done when AWS is not available."""
        with (
            patch(f"{MODULE}.is_taskable", return_value=False),
            patch(f"{MODULE}.destroy_domain_A_record") as destroy_domain_A_record,
        ):
            undeploy_default_api(llmclient_id=self.llmclient.pk)
        destroy_domain_A_record.assert_not_called()
        self.assertEqual(
            LLMClient.objects.get(pk=self.llmclient.pk).dns_verification_status,
            LLMClient.DnsVerificationStatusChoices.VERIFIED,
        )


class TestUndeployDeployRace(TestAccountMixin):
    """
    Test that an llmclient's undeploy and deploy tasks, which run on different workers, do not race.

    Each task runs in its own thread, with its own database connection, as on two Celery workers.
    """

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_undeploy_deploy_race_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.events: list[str] = []
        self.destroying = threading.Event()
        self.release = threading.Event()
        infrastructure = MagicMock()
        infrastructure.dns.create_domain_a_record.side_effect = lambda **kwargs: (
            self.events.append("created") or ({}, True)
        )
        settings = MagicMock(llmclient_tasks_create_dns_record=True, llmclient_tasks_create_ingress_manifest=True)
        for target in (
            patch(f"{MODULE}.is_taskable", return_value=True),
            patch(f"{MODULE}.destroy_domain_A_record", side_effect=self.destroy),
            patch(f"{DEPLOY_MODULE}.is_taskable", return_value=True),
            patch(f"{DEPLOY_MODULE}.infrastructure", infrastructure),
            patch(f"{DEPLOY_MODULE}.smarter_settings", settings),
            patch(f"{DEPLOY_MODULE}.apply_ingress_manifest"),
            patch(f"{DEPLOY_MODULE}.continue_default_api_deployment"),
        ):
            target.start()
            self.addCleanup(target.stop)

    def destroy(self, **kwargs):
        """Destroy the A record, slowly: wait until the test releases it."""
        self.destroying.set()
        self.release.wait(timeout=10)
        self.events.append("destroyed")

    @staticmethod
    def in_thread(task, llmclient_id: int) -> threading.Thread:
        def run():
            try:
                task(llmclient_id=llmclient_id)
            finally:
                connection.close()

        thread = threading.Thread(target=run)
        thread.start()
        return thread

    def test_deploy_waits_for_undeploy(self):
        """
        Test that a deploy that starts while an undeploy is destroying the A record waits for it.

        Before the lock, the deploy could read the llmclient's state, or create its A record, before
        the undeploy destroyed the record and saved the state. It then left the llmclient without an
        A record, or took it to be deployed and verified already, and did nothing.
        """
        LLMClient.objects.filter(pk=self.llmclient.pk).update(
            deployed=False, dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFIED
        )
        undeploy = self.in_thread(undeploy_default_api, self.llmclient.pk)
        self.assertTrue(self.destroying.wait(timeout=10))
        deploy = self.in_thread(deploy_default_api, self.llmclient.pk)
        deploy.join(timeout=1)
        self.assertTrue(deploy.is_alive(), "the deploy did not wait for the undeploy's lock")
        self.release.set()
        undeploy.join(timeout=10)
        deploy.join(timeout=10)

        self.assertEqual(self.events, ["destroyed", "created"])
        llmclient = LLMClient.objects.get(pk=self.llmclient.pk)
        self.assertEqual(llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED)
        # the deploy went on to issue the certificate and verify the domain, rather than doing nothing.
        self.assertEqual(
            llmclient.tls_certificate_issuance_status, LLMClient.TlsCertificateIssuanceStatusChoices.REQUESTED
        )
