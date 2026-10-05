"""
Test :mod:`smarter.apps.llmclient.tasks.deploy_custom_api`, and what triggers it.

The task is called directly, which runs it synchronously, in this process. AWS and Kubernetes are
mocked: no DNS record or ingress is created.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
from smarter.apps.llmclient.signals import llmclient_deployed
from smarter.apps.llmclient.tasks.deploy_custom_api import deploy_custom_api
from smarter.apps.llmclient.tasks.verify_custom_domain import verify_custom_domain

MODULE = "smarter.apps.llmclient.tasks.deploy_custom_api"
Status = LLMClientCustomDomain.VerificationStatusChoices


class TestDeployCustomApi(TestAccountMixin):
    """Test that a deployed llmclient with a verified custom domain is deployed on its custom host."""

    def setUp(self):
        super().setUp()
        self.domain_name = f"test-custom-api-{self.hash_suffix}.example.com".lower()
        self.custom_domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile, domain_name=self.domain_name, aws_hosted_zone_id="ZCUSTOMAPI"
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=self.custom_domain.pk).delete)
        self.llmclient = LLMClient.objects.create(
            name=f"test_custom_api_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        # update(), rather than save(), which sends llmclient signals, and would queue real deployments.
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=True, custom_domain=self.custom_domain)

        settings = MagicMock(llmclient_tasks_create_dns_record=True, llmclient_tasks_create_ingress_manifest=True)
        aws_helper = MagicMock()
        aws_helper.route53.create_domain_a_record.return_value = ({}, True)
        for target, value in (
            ("is_taskable", MagicMock(return_value=True)),
            ("aws_helper", aws_helper),
            ("apply_ingress_manifest", MagicMock()),
            ("smarter_settings", settings),
        ):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def verify(self):
        self.custom_domain.set_verification_status(Status.VERIFIED)

    def refreshed_llmclient(self) -> LLMClient:
        return LLMClient.objects.get(pk=self.llmclient.pk)

    # -------------------------------------------------------------------------
    # the task
    # -------------------------------------------------------------------------
    def test_deploy(self):
        """The custom host gets an A record in the custom domain's hosted zone, and an ingress."""
        self.verify()
        llmclient = self.refreshed_llmclient()
        custom_host = deploy_custom_api(self.llmclient.pk)
        self.assertEqual(custom_host, llmclient.custom_host)
        self.assertEqual(custom_host, f"{llmclient.rfc1034_compliant_name}.{self.domain_name}")
        self.aws_helper.route53.create_domain_a_record.assert_called_once_with(
            hostname=custom_host, api_host_domain=llmclient.base_api_domain, hosted_zone_id="ZCUSTOMAPI"
        )
        self.apply_ingress_manifest.assert_called_once_with(custom_host)

    def test_custom_domain_not_verified(self):
        self.assertIsNone(deploy_custom_api(self.llmclient.pk))
        self.aws_helper.route53.create_domain_a_record.assert_not_called()
        self.apply_ingress_manifest.assert_not_called()

    def test_llmclient_not_deployed(self):
        self.verify()
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=False)
        self.assertIsNone(deploy_custom_api(self.llmclient.pk))
        self.apply_ingress_manifest.assert_not_called()

    def test_no_custom_domain(self):
        LLMClient.objects.filter(pk=self.llmclient.pk).update(custom_domain=None)
        self.assertIsNone(deploy_custom_api(self.llmclient.pk))
        self.apply_ingress_manifest.assert_not_called()

    def test_unknown_llmclient(self):
        self.assertIsNone(deploy_custom_api(999999999))
        self.apply_ingress_manifest.assert_not_called()

    def test_settings_disable_dns_and_ingress(self):
        self.verify()
        self.smarter_settings.llmclient_tasks_create_dns_record = False
        self.smarter_settings.llmclient_tasks_create_ingress_manifest = False
        self.assertIsNotNone(deploy_custom_api(self.llmclient.pk))
        self.aws_helper.route53.create_domain_a_record.assert_not_called()
        self.apply_ingress_manifest.assert_not_called()

    # -------------------------------------------------------------------------
    # what triggers it
    # -------------------------------------------------------------------------
    def test_deployed_llmclient_with_verified_domain_is_deployed_on_its_custom_host(self):
        self.verify()
        with patch("smarter.apps.llmclient.receivers.deploy_custom_api") as task:
            llmclient_deployed.send(sender=self.__class__, llmclient=self.refreshed_llmclient())
        task.delay.assert_called_once_with(llmclient_id=self.llmclient.pk)

    def test_deployed_llmclient_without_verified_domain_is_not(self):
        with patch("smarter.apps.llmclient.receivers.deploy_custom_api") as task:
            llmclient_deployed.send(sender=self.__class__, llmclient=self.refreshed_llmclient())
        task.delay.assert_not_called()

    def test_verified_domain_deploys_its_llmclient(self):
        """Once its custom domain is verified, the deployed llmclient that uses it is deployed on it."""
        verify_module = "smarter.apps.llmclient.tasks.verify_custom_domain"
        aws_helper = MagicMock()
        aws_helper.route53.get_hosted_zone_by_id.return_value = {"HostedZone": {"Name": f"{self.domain_name}."}}
        with (
            patch(f"{verify_module}.is_taskable", return_value=True),
            patch(f"{verify_module}.aws_helper", aws_helper),
            patch(f"{verify_module}.AccountContact"),
            patch(f"{verify_module}._verification_blocker", return_value=None),
            patch.object(deploy_custom_api, "delay") as delay,
        ):
            self.assertTrue(verify_custom_domain("ZCUSTOMAPI"))
        delay.assert_called_once_with(llmclient_id=self.llmclient.pk)
