# pylint: disable=W0613
"""Tests for manage.py create_plugin."""

import time

from django.core.management import call_command
from django.test import tag

from smarter.apps.account.models import Account
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.providers.aws import AWSProvider
from smarter.apps.llmclient.models import LLMClient, LLMClientAPIKey
from smarter.apps.llmclient.signals import (
    llmclient_dns_failed,
    llmclient_dns_verification_initiated,
    llmclient_dns_verification_status_changed,
    llmclient_dns_verified,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_LLM_CLIENT_NAME
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.unittest.runner import INFRASTRUCTURE

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


# pylint: disable=too-many-instance-attributes
class ManageCommandCreatePluginTestCase(TestAccountMixin):
    """Tests for manage.py create_plugin."""

    _llmclient_dns_verification_status_changed = False
    _llmclient_dns_failed = False
    _llmclient_dns_verification_initiated = False
    _llmclient_dns_verified = False

    def llmclient_dns_verification_status_changed_signal_handler(self, *args, **kwargs):
        self._llmclient_dns_verification_status_changed = True

    def llmclient_dns_failed_signal_handler(self, *args, **kwargs):
        self._llmclient_dns_failed = True

    def llmclient_dns_verification_initiated_signal_handler(self, *args, **kwargs):
        self._llmclient_dns_verification_initiated = True

    def llmclient_dns_verified_signal_handler(self, *args, **kwargs):
        self._llmclient_dns_verified = True

    @property
    def signals(self):
        return {
            "llmclient_dns_verification_status_changed": self._llmclient_dns_verification_status_changed,
            "llmclient_dns_failed": self._llmclient_dns_failed,
            "llmclient_dns_verification_initiated": self._llmclient_dns_verification_initiated,
            "llmclient_dns_verified": self._llmclient_dns_verified,
        }

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.auth_token, self.secret_key = SmarterAuthToken.objects.create(
            user_profile=self.user_profile, name="testKey", user=self.admin_user, description="unit test"
        )  # type: ignore
        self.llmclient = LLMClient.objects.create(
            user_profile=self.user_profile,
            name="manage-command-create-plugin-test-case",
        )
        self._llmclient_dns_verification_status_changed = False
        self._llmclient_dns_failed = False
        self._llmclient_dns_verification_initiated = False
        self._llmclient_dns_verified = False

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            if self.llmclient is not None:
                self.llmclient.delete()
        except LLMClient.DoesNotExist:
            pass
        try:
            if self.auth_token is not None:
                self.auth_token.delete()
        except SmarterAuthToken.DoesNotExist:
            pass
        super().tearDown()

    def test_add_api_key(self):
        """Test add_api_key command."""

        call_command(
            "add_api_key",
            "--account_number",
            f"{self.account.account_number}",
            "--key_id",
            self.auth_token.key_id,
            "--name",
            self.llmclient.name,
        )

        llmclient_api_key = LLMClientAPIKey.objects.get(api_key=self.auth_token)
        self.assertEqual(llmclient_api_key.llmclient, self.llmclient)

    def test_llmclient_dns_status_signals(self):
        llmclient_dns_verification_status_changed.connect(
            self.llmclient_dns_verification_status_changed_signal_handler,
            dispatch_uid="llmclient_dns_verification_status_changed_test_plugin_called_signal",
        )
        llmclient_dns_failed.connect(
            self.llmclient_dns_failed_signal_handler, dispatch_uid="llmclient_dns_failed_test_plugin_called_signal"
        )
        llmclient_dns_verification_initiated.connect(
            self.llmclient_dns_verification_initiated_signal_handler,
            dispatch_uid="llmclient_dns_verification_initiated_test_plugin_called_signal",
        )
        llmclient_dns_verified.connect(
            self.llmclient_dns_verified_signal_handler,
            dispatch_uid="llmclient_dns_verified_test_plugin_called_signal",
        )

        self.llmclient.dns_verification_status = LLMClient.DnsVerificationStatusChoices.VERIFYING
        self.llmclient.save()
        time.sleep(1)
        self.assertTrue(self.signals["llmclient_dns_verification_status_changed"])
        self.assertTrue(self.signals["llmclient_dns_verification_initiated"])

        self._llmclient_dns_verification_status_changed = False
        self.llmclient.dns_verification_status = LLMClient.DnsVerificationStatusChoices.FAILED
        self.llmclient.save()
        time.sleep(1)
        self.assertTrue(self.signals["llmclient_dns_verification_status_changed"])
        self.assertTrue(self.signals["llmclient_dns_failed"])

        self._llmclient_dns_verification_status_changed = False
        self.llmclient.dns_verification_status = LLMClient.DnsVerificationStatusChoices.VERIFIED
        self.llmclient.save()
        time.sleep(1)
        self.assertTrue(self.signals["llmclient_dns_verification_status_changed"])
        self.assertTrue(self.signals["llmclient_dns_verified"])

        self._llmclient_dns_verification_status_changed = False
        self.llmclient.dns_verification_status = LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED
        self.llmclient.save()
        time.sleep(1)
        self.assertTrue(self.signals["llmclient_dns_verification_status_changed"])

    @tag(INFRASTRUCTURE)
    def test_deploy_and_undeploy(self):
        """Test deploy_llmclient and undeploy_llmclient commands."""

        #######################################################################
        # Deploy the llmclient
        #######################################################################
        print("test_deploy_and_undeploy(): initiating deploy...")
        print("-" * 80)

        # the DNS zone of the customer api domain. This test is tagged INFRASTRUCTURE, so it may use real AWS.
        dns = AWSProvider(allow_in_tests=True).dns
        api_zone = dns.get_zone(smarter_settings.environment_api_domain)
        if api_zone is None:
            self.fail(f"DNS zone not found for {smarter_settings.environment_api_domain}")
        api_hosted_zone_id = api_zone.id

        call_command(
            "deploy_llmclient", "--account_number", f"{self.account.account_number}", "--name", self.llmclient.name
        )
        print("sleeping for 15 seconds to allow DNS record to be created")
        time.sleep(15)
        llmclient = LLMClient.objects.get(name=self.llmclient.name, user_profile__account=self.account)
        print(f"found llmclient.id={llmclient.id} llmclient.default_host={llmclient.default_host}")

        # verify that a DNS record was created for the llmclient
        llmclient_default_host = llmclient.default_host
        a_record = dns.get_record(api_hosted_zone_id, llmclient_default_host, "A")
        if a_record is None:
            self.fail(f"DNS A record not found for zone {api_hosted_zone_id}, {llmclient_default_host}")
        self.assertEqual(a_record.name, dns.resolve_domain(llmclient_default_host))

        # verify that the dns record verification is either underway or completed
        print("llmclient.dns_verification_status", llmclient.dns_verification_status)
        self.assertIn(
            llmclient.dns_verification_status,
            [llmclient.DnsVerificationStatusChoices.VERIFYING, llmclient.DnsVerificationStatusChoices.VERIFIED],
        )

        #######################################################################
        # Undeploy the llmclient
        #######################################################################
        print("test_deploy_and_undeploy(): initiating undeploy...")
        print("-" * 80)

        call_command(
            "undeploy_llmclient",
            "--account_number",
            f"{self.account.account_number}",
            "--name",
            self.llmclient.name,
            "--foreground",
        )
        llmclient = LLMClient.objects.get(name=self.llmclient.name, user_profile__account=self.account)
        self.assertEqual(llmclient.deployed, False)
        self.assertEqual(llmclient.dns_verification_status, llmclient.DnsVerificationStatusChoices.NOT_VERIFIED)
        a_record = dns.get_record(api_hosted_zone_id, llmclient_default_host, "A")
        if a_record is not None:
            logger.info("test_deploy_and_undeploy() found an existing DNS record: %s", a_record)
            self.assertEqual(a_record.name, dns.resolve_domain(llmclient_default_host))

    @tag(INFRASTRUCTURE)
    def test_deploy_demo_api(self):
        """Test deploy_example_llmclient command."""
        call_command("deploy_example_llmclient")
        print("sleeping for 15 seconds to allow DNS record to be created")
        time.sleep(15)

        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        llmclient = LLMClient.objects.get(name=SMARTER_EXAMPLE_LLM_CLIENT_NAME, user_profile__account=account)
        self.assertIn(
            llmclient.dns_verification_status,
            [llmclient.DnsVerificationStatusChoices.VERIFYING, llmclient.DnsVerificationStatusChoices.VERIFIED],
        )

    def test_initialize_waffle(self):
        """Test initialize_waffle command."""
        call_command("initialize_waffle")

    def test_load_from_github_v1(self):
        """Test load_from_github command."""

        call_command(
            "load_from_github",
            "--account_number",
            f"{self.account.account_number}",
            "--url",
            "https://github.com/QueriumCorp/smarter-demo",
            "--username",
            self.admin_user.get_username(),
        )

    def test_load_from_github_v2(self):
        """Test load_from_github command."""

        call_command(
            "load_from_github",
            "--account_number",
            f"{self.account.account_number}",
            "--url",
            "https://github.com/smarter-sh/examples",
            "--username",
            self.admin_user.get_username(),
            "--repo_version",
            "2",
        )

    @tag(INFRASTRUCTURE)
    def test_verify_api_infrastructure(self):
        """Test verify_dns_configuration command."""

        call_command("verify_dns_configuration")
