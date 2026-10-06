"""
Test :mod:`smarter.apps.llmclient.tasks.deploy_default_api`.

The tasks are called directly, which runs them synchronously, in this process. The infrastructure
services are mocked: no DNS record, ingress or certificate is read or created.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import deploy_default_api as module
from smarter.apps.llmclient.tasks.deploy_default_api import (
    CERTIFICATE_CHECK_INTERVAL,
    CERTIFICATE_MAX_ATTEMPTS,
    STAGE_CERTIFICATE,
    STAGE_DOMAIN,
    continue_default_api_deployment,
    deploy_default_api,
)
from smarter.apps.llmclient.tasks.verify_domain import (
    VERIFY_DOMAIN_INTERVAL,
    DomainCheck,
)
from smarter.common.exceptions import SmarterException

MODULE = "smarter.apps.llmclient.tasks.deploy_default_api"


class TestContinueDefaultApiDeployment(TestAccountMixin):
    """Test that a deployment checks its certificate and domain without blocking a worker."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_deploy_default_api_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        infrastructure = MagicMock()
        infrastructure.dns.resolve_domain.side_effect = lambda domain: domain
        for target, value in (
            ("is_taskable", MagicMock(return_value=True)),
            ("infrastructure", infrastructure),
            # applies the ingress manifest with the real infrastructure services, in tasks.utils.
            ("apply_ingress_manifest", MagicMock()),
            ("AccountContact", MagicMock()),
        ):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)
        patcher = patch.object(continue_default_api_deployment, "apply_async")
        self.apply_async = patcher.start()
        self.addCleanup(patcher.stop)

    def resources(self, ready: bool):
        """Set whether the ingress, certificate and secret are ready."""
        self.infrastructure.kubernetes.verify_ingress_resources.return_value = (ready, ready, ready)

    def refresh(self) -> LLMClient:
        return LLMClient.objects.get(pk=self.llmclient.pk)

    def scheduled(self) -> dict:
        """Return the kwargs and countdown of the run that was scheduled."""
        self.apply_async.assert_called_once()
        call = self.apply_async.call_args
        return {**call.kwargs["kwargs"], "countdown": call.kwargs["countdown"]}

    def test_does_not_sleep(self):
        """Test that the module no longer sleeps: it schedules itself to check again instead."""
        self.assertFalse(hasattr(module, "time"))

    def test_certificate_not_ready_checks_again(self):
        """Test that a certificate that is not issued yet is checked again later, without waiting."""
        self.resources(ready=False)
        continue_default_api_deployment(self.llmclient.pk, stage=STAGE_CERTIFICATE, attempt=0)
        self.infrastructure.kubernetes.verify_ingress_resources.assert_called_once()
        self.assertEqual(self.infrastructure.kubernetes.verify_ingress_resources.call_args.kwargs["max_attempts"], 1)
        scheduled = self.scheduled()
        self.assertEqual(scheduled["stage"], STAGE_CERTIFICATE)
        self.assertEqual(scheduled["attempt"], 1)
        self.assertEqual(scheduled["countdown"], CERTIFICATE_CHECK_INTERVAL)

    def test_certificate_never_ready_fails(self):
        """Test that a certificate that is still not issued after the last check fails the deployment."""
        self.resources(ready=False)
        continue_default_api_deployment(
            self.llmclient.pk, stage=STAGE_CERTIFICATE, attempt=CERTIFICATE_MAX_ATTEMPTS - 1
        )
        self.apply_async.assert_not_called()
        self.assertEqual(
            self.refresh().tls_certificate_issuance_status, LLMClient.TlsCertificateIssuanceStatusChoices.FAILED
        )

    def test_certificate_ready_then_domain_pending(self):
        """Test that an issued certificate goes on to the domain, which is checked again later if it does not resolve."""
        self.resources(ready=True)
        with patch(f"{MODULE}.check_domain", return_value=DomainCheck.PENDING):
            continue_default_api_deployment(self.llmclient.pk, stage=STAGE_CERTIFICATE)
        llmclient = self.refresh()
        self.assertEqual(
            llmclient.tls_certificate_issuance_status, LLMClient.TlsCertificateIssuanceStatusChoices.ISSUED
        )
        self.assertEqual(llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.VERIFYING)
        scheduled = self.scheduled()
        self.assertEqual((scheduled["stage"], scheduled["attempt"]), (STAGE_DOMAIN, 1))
        self.assertEqual(scheduled["countdown"], VERIFY_DOMAIN_INTERVAL)

    def test_domain_verified_activates(self):
        """Test that a domain that resolves activates the llmclient, and notifies its account."""
        with patch(f"{MODULE}.check_domain", return_value=DomainCheck.VERIFIED):
            continue_default_api_deployment(self.llmclient.pk, stage=STAGE_DOMAIN, attempt=3)
        llmclient = self.refresh()
        self.assertTrue(llmclient.deployed)
        self.assertEqual(llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.VERIFIED)
        self.AccountContact.send_email_to_primary_contact.assert_called_once()
        self.apply_async.assert_not_called()

    def test_domain_missing_fails(self):
        """Test that a domain whose DNS record does not exist fails at once, without checking again."""
        with patch(f"{MODULE}.check_domain", return_value=DomainCheck.MISSING):
            continue_default_api_deployment(self.llmclient.pk, stage=STAGE_DOMAIN)
        self.apply_async.assert_not_called()
        llmclient = self.refresh()
        self.assertFalse(llmclient.deployed)
        self.assertEqual(llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.FAILED)

    def test_without_domain_verification(self):
        """Test that a deployment without domain verification is completed when its certificate is issued."""
        self.resources(ready=True)
        with patch(f"{MODULE}.check_domain") as check_domain:
            continue_default_api_deployment(self.llmclient.pk, with_domain_verification=False)
        check_domain.assert_not_called()
        self.assertEqual(self.refresh().dns_verification_status, LLMClient.DnsVerificationStatusChoices.VERIFIED)

    def test_unknown_llmclient(self):
        """Test that the continuation of an llmclient that was deleted does nothing."""
        continue_default_api_deployment(999999999, stage=STAGE_CERTIFICATE)
        self.infrastructure.kubernetes.verify_ingress_resources.assert_not_called()
        self.apply_async.assert_not_called()


class TestDeployDefaultApi(TestAccountMixin):
    """Test that deploy_default_api creates the DNS record and ingress, then hands off to its continuation."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_deploy_default_api_start_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.infrastructure = MagicMock()
        self.infrastructure.dns.create_domain_a_record.return_value = ({}, True)
        self.settings = MagicMock(llmclient_tasks_create_dns_record=True, llmclient_tasks_create_ingress_manifest=True)
        for target, value in (
            ("is_taskable", MagicMock(return_value=True)),
            ("infrastructure", self.infrastructure),
            ("smarter_settings", self.settings),
            ("apply_ingress_manifest", MagicMock()),
            ("continue_default_api_deployment", MagicMock()),
        ):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def set_certificate_status(self, status):
        # update(), rather than save(), which would queue a real deployment.
        LLMClient.objects.filter(pk=self.llmclient.pk).update(tls_certificate_issuance_status=status)

    def test_not_taskable(self):
        """Test that nothing is done when the infrastructure services are not available."""
        self.is_taskable.return_value = False
        self.assertIsNone(deploy_default_api(self.llmclient.pk))
        self.infrastructure.dns.create_domain_a_record.assert_not_called()

    def test_unknown_llmclient(self):
        """Test that an llmclient that doesn't exist is not deployed."""
        self.assertIsNone(deploy_default_api(999999999))
        self.infrastructure.dns.create_domain_a_record.assert_not_called()

    def test_dns_not_ready(self):
        """Test that nothing is deployed when the DNS service is not ready."""
        self.infrastructure.dns.ready = False
        self.assertIsNone(deploy_default_api(self.llmclient.pk))
        self.continue_default_api_deployment.assert_not_called()

    def test_already_deployed_and_verified(self):
        """Test that an llmclient that is deployed and verified only has its DNS record verified."""
        self.infrastructure.dns.create_domain_a_record.return_value = ({}, False)
        LLMClient.objects.filter(pk=self.llmclient.pk).update(
            deployed=True, dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFIED
        )
        deploy_default_api(self.llmclient.pk)
        self.infrastructure.dns.create_domain_a_record.assert_called_once()
        self.apply_ingress_manifest.assert_not_called()
        self.continue_default_api_deployment.assert_not_called()

    def test_without_ingress_manifest(self):
        """Test that the domain is verified next when the ingress manifest is not created."""
        self.settings.llmclient_tasks_create_ingress_manifest = False
        deploy_default_api(self.llmclient.pk)
        self.apply_ingress_manifest.assert_not_called()
        self.continue_default_api_deployment.assert_called_once()
        self.assertEqual(self.continue_default_api_deployment.call_args.kwargs["stage"], STAGE_DOMAIN)

    def test_ingress_manifest_fails(self):
        """Test that a failure to apply the ingress manifest fails the certificate issuance."""
        self.apply_ingress_manifest.side_effect = SmarterException("test ingress error")
        deploy_default_api(self.llmclient.pk)
        self.continue_default_api_deployment.assert_not_called()
        self.assertEqual(
            LLMClient.objects.get(pk=self.llmclient.pk).tls_certificate_issuance_status,
            LLMClient.TlsCertificateIssuanceStatusChoices.FAILED,
        )

    def test_certificate_requested_checks_later(self):
        """Test that a certificate that is not issued yet is requested, and checked later."""
        deploy_default_api(self.llmclient.pk)
        self.apply_ingress_manifest.assert_called_once_with(self.llmclient.default_host)
        self.continue_default_api_deployment.apply_async.assert_called_once()
        call = self.continue_default_api_deployment.apply_async.call_args
        self.assertEqual(call.kwargs["kwargs"]["stage"], STAGE_CERTIFICATE)
        self.assertEqual(
            LLMClient.objects.get(pk=self.llmclient.pk).tls_certificate_issuance_status,
            LLMClient.TlsCertificateIssuanceStatusChoices.REQUESTED,
        )

    def test_certificate_issued_continues(self):
        """Test that the certificate of an llmclient whose certificate is issued is verified at once."""
        self.set_certificate_status(LLMClient.TlsCertificateIssuanceStatusChoices.ISSUED)
        deploy_default_api(self.llmclient.pk)
        self.continue_default_api_deployment.apply_async.assert_not_called()
        self.continue_default_api_deployment.assert_called_once()
        self.assertEqual(self.continue_default_api_deployment.call_args.kwargs["stage"], STAGE_CERTIFICATE)
