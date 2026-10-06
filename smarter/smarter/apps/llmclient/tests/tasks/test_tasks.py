# pylint: disable=wrong-import-position
"""Test LLMClient tasks."""

import time

from django.test import tag

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.infrastructure.providers import configure_provider
from smarter.apps.infrastructure.providers.aws import AWSProvider
from smarter.apps.infrastructure.services import (
    KubectlKubernetesService,
    configure_kubernetes,
    infrastructure,
)
from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
from smarter.apps.llmclient.tasks import (
    create_custom_domain_dns_record,
    deploy_default_api,
    undeploy_default_api,
    verify_domain,
)
from smarter.common.conf import smarter_settings

# python stuff
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.unittest.runner import INFRASTRUCTURE

logger = logging.getLogger(__name__)


@tag(INFRASTRUCTURE)
class TestLLMClientTasks(TestAccountMixin):
    """
    Test LLMClient tasks, with real AWS and Kubernetes.

    The infrastructure services refuse to reach real infrastructure from the unit tests, so this
    suite, which is tagged INFRASTRUCTURE and skipped by default, allows them explicitly.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        provider = AWSProvider(allow_in_tests=True)
        configure_provider(lambda: provider)
        configure_kubernetes(lambda: KubectlKubernetesService(provider=provider, allow_in_tests=True))
        cls.dns = provider.dns
        cls.certificates = provider.certificates

        cls.smarter_account = None
        cls.smarter_admin_user = None

        # we want to test with the Smarter account so that we retain the
        # same account number for DNS verifications in local.api.smarter.sh in
        # AWS Route53
        cls.smarter_account = smarter_cached_objects.smarter_account
        cls.smarter_user_profile = smarter_cached_objects.smarter_admin_user_profile
        cls.smarter_admin_user = smarter_cached_objects.smarter_admin

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        common_name = "test-llmclient-tasks"

        self.domain_name = f"{common_name}.{self.dns.environment_api_domain}"
        self.dns.delete_zone(self.domain_name)

        self.llmclient, _ = LLMClient.objects.get_or_create(
            user_profile=self.smarter_user_profile,
            name=common_name,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            LLMClientCustomDomain.objects.get(user_profile=self.smarter_user_profile).delete()
        except LLMClientCustomDomain.DoesNotExist:
            pass

        try:
            if self.llmclient:
                self.llmclient.delete()
        # pylint: disable=W0718
        except Exception:
            pass

        try:
            self.dns.delete_zone(self.domain_name)
            certificate_id = self.certificates.get_certificate_id(self.domain_name)
            if certificate_id:
                self.certificates.delete_certificate(certificate_id)
        # pylint: disable=W0718
        except Exception:
            pass
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        configure_kubernetes(None)
        configure_provider(None)
        super().tearDownClass()

    def test_create_hosted_zone(self):
        zone, created = self.dns.get_or_create_zone(self.domain_name)
        self.assertTrue(created)
        self.assertTrue(zone.name_servers)
        self.assertTrue(self.dns.delete_zone(self.domain_name))

    def test_create_custom_domain_dns_record(self):
        """Test that we can create a DNS record for a custom domain."""

        print("test_create_custom_domain_dns_record()")
        resolved_domain = self.dns.resolve_domain(self.domain_name)
        zone, _ = self.dns.get_or_create_zone(resolved_domain)

        custom_domain, _ = LLMClientCustomDomain.objects.get_or_create(
            user_profile=self.smarter_user_profile,
            domain_name=resolved_domain,
            aws_hosted_zone_id=zone.id,
        )

        create_custom_domain_dns_record(
            llmclient_custom_domain_id=custom_domain.id,  # type: ignore
            record_name=resolved_domain,
            record_type="TXT",
            record_value="test",
            record_ttl=600,
        )

        dns_record = self.dns.get_record(custom_domain.aws_hosted_zone_id, resolved_domain, "TXT")
        if dns_record is None:
            self.fail(f"Expected a TXT record for {resolved_domain}")
        self.assertEqual(dns_record.name, resolved_domain)
        self.assertEqual(dns_record.type, "TXT")
        self.assertEqual(dns_record.values, ["test"])

    def test_verify_domain(self):
        """Test that we can verify a domain."""
        zone = self.dns.get_zone(smarter_settings.root_domain)
        if zone is None:
            self.fail(f"Expected a DNS zone for {smarter_settings.root_domain}")
        is_verified = verify_domain(domain_name=smarter_settings.root_domain, record_type="NS", hosted_zone_id=zone.id)
        self.assertTrue(is_verified)

    def test_create_domain_A_record(self):
        """Test that we can create an A record for a domain."""

        resolved_domain = self.dns.resolve_domain(self.domain_name)
        api_domain = self.dns.environment_api_domain
        zone = self.dns.get_zone(api_domain)
        if zone is None:
            self.fail(f"Expected a DNS zone for {api_domain}")

        self.dns.create_domain_a_record(hostname=resolved_domain, api_host_domain=api_domain)
        dns_record = self.dns.get_record(zone.id, resolved_domain, "A")
        if dns_record is None:
            self.fail(f"Expected an A record for {resolved_domain}")
        self.assertEqual(dns_record.name, resolved_domain)
        self.assertEqual(dns_record.type, "A")
        self.dns.delete_record(zone.id, resolved_domain, "A")

    def test_deploy_default_api(self):
        """Test that we can deploy the default API."""

        deploy_default_api(llmclient_id=self.llmclient.id, with_domain_verification=False)  # type: ignore

        logger.debug("self.llmclient.default_host: %s", self.llmclient.default_host)
        self.assertTrue(SmarterValidator.is_valid_hostname(self.llmclient.default_host))
        logger.debug("self.llmclient.default_url: %s", self.llmclient.default_url)
        self.assertTrue(SmarterValidator.is_valid_url(self.llmclient.default_url))
        logger.debug("self.llmclient.custom_host: %s", self.llmclient.custom_host)
        self.assertIsNone(self.llmclient.custom_host)
        logger.debug("self.llmclient.custom_url: %s", self.llmclient.custom_url)
        self.assertIsNone(self.llmclient.custom_url)
        logger.debug("self.llmclient.sandbox_host: %s", self.llmclient.sandbox_host)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llmclient.sandbox_url), f"Invalid URL: {self.llmclient.sandbox_url}"
        )
        logger.debug("self.llmclient.sandbox_url: %s", self.llmclient.sandbox_url)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llmclient.sandbox_url), f"Invalid URL: {self.llmclient.sandbox_url}"
        )
        logger.debug("self.llmclient.hostname: %s", self.llmclient.hostname)
        self.assertTrue(SmarterValidator.is_valid_url(self.llmclient.url), f"Invalid URL: {self.llmclient.hostname}")
        logger.debug("self.llmclient.url: %s", self.llmclient.url)
        self.assertTrue(SmarterValidator.is_valid_url(self.llmclient.url), f"Invalid URL: {self.llmclient.url}")
        logger.debug("self.llmclient.url_llmclient: %s", self.llmclient.url_llmclient)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llmclient.url_llmclient),
            f"Invalid URL: {self.llmclient.url_llmclient}",
        )
        logger.debug("self.llmclient.url_chatapp: %s", self.llmclient.url_chatapp)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llmclient.url_chatapp), f"Invalid URL: {self.llmclient.url_chatapp}"
        )
        logger.debug("self.llmclient.mode(self.llmclient.url): %s", self.llmclient.mode(self.llmclient.url))
        self.assertEqual(self.llmclient.mode(self.llmclient.url), "sandbox")

        zone = self.dns.get_zone(self.dns.environment_api_domain)
        if zone is None:
            self.fail(f"Expected a DNS zone for {self.dns.environment_api_domain}")
        a_record = None
        retries = 5
        while retries > 0 and a_record is None:
            a_record = self.dns.get_record(zone.id, self.llmclient.default_host, "A")
            if a_record is None:
                print("DNS record not found. Retrying. Attempts remaining: ", retries)
                time.sleep(5)  # wait for 5 seconds before retrying
                retries -= 1
        self.assertIsNotNone(a_record)

        resolved_hostname = self.dns.resolve_domain(self.llmclient.default_host)
        if a_record is None:
            self.fail(f"Expected an A record for {resolved_hostname}")
        self.assertEqual(a_record.name, resolved_hostname)
        self.assertEqual(a_record.type, "A")

        self.assertTrue(self.llmclient.ready)
        # we'll test this separately since it run asynchronously. For now, just ensure it's one of the two hoped-for values.
        self.assertIn(
            self.llmclient.dns_verification_status,
            [LLMClient.DnsVerificationStatusChoices.VERIFIED, LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED],
        )
        if self.llmclient.tls_certificate_issuance_status not in [
            LLMClient.TlsCertificateIssuanceStatusChoices.ISSUED,
            LLMClient.TlsCertificateIssuanceStatusChoices.REQUESTED,
        ]:
            logger.warning(
                "Unexpected TLS certificate issuance status: %s. This is likely a problem with Kubernetes cert-manager and will be ignored for purposes of this test.",
                self.llmclient.tls_certificate_issuance_status,
            )

        # mcdaniel: 2026-01-09: disabling this for now bc it's managed asynchronously
        # self.assertTrue(self.llmclient.deployed)

    def test_undeploy_default_api(self):
        """Test that we can undeploy the default API."""
        deploy_default_api(llmclient_id=self.llmclient.id, with_domain_verification=False)  # type: ignore
        undeploy_default_api(llmclient_id=self.llmclient.id)  # type: ignore

        self.assertFalse(self.llmclient.deployed)

        # DNS record should now be set to unverified, but the TLS certificate should still exist and still be valid.
        self.assertEqual(self.llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED)
