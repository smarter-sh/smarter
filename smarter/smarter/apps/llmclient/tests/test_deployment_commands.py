"""
Test the llmclient deployment management commands: deploy_llmclient, undeploy_llmclient, deploy_example_llmclient, register_custom_domain and verify_custom_domain.

Deploying an llmclient creates real Route53 records, so nothing here lets a
deployment reach AWS: LLMClient.save() is mocked wherever it would send
llmclient_deploy, and the Celery tasks and aws_helper are mocked in each
command's module.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
from smarter.common.const import SMARTER_EXAMPLE_LLM_CLIENT_NAME
from smarter.common.exceptions import SmarterValueError

COMMANDS = "smarter.apps.llmclient.management.commands"


class DeploymentCommandTestBase(TestAccountMixin):
    """Run a management command, and return its output."""

    def run_command(self, command_name: str, *args, **options) -> str:
        out = StringIO()
        call_command(command_name, *args, stdout=out, stderr=out, **options)
        return out.getvalue()

    def create_llmclient(self, name: str, deployed: bool = False) -> LLMClient:
        llmclient = LLMClient.objects.create(name=name, user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        if deployed:
            # update(), rather than save(), which would queue a real deployment.
            LLMClient.objects.filter(pk=llmclient.pk).update(
                deployed=True, dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFIED
            )
        return llmclient


class TestDeployLLMClient(DeploymentCommandTestBase):
    """Test manage.py deploy_llmclient."""

    def setUp(self):
        super().setUp()
        self.llmclient = self.create_llmclient(f"test_deploy_cmd_{self.hash_suffix}")

    def test_deploy_by_account_number(self):
        with patch.object(LLMClient, "save", autospec=True) as save:
            self.run_command("deploy_llmclient", account_number=self.account.account_number, name=self.llmclient.name)
        save.assert_called_once()
        deployed_llmclient = save.call_args.args[0]
        self.assertEqual(deployed_llmclient.pk, self.llmclient.pk)
        self.assertTrue(deployed_llmclient.deployed)

    def test_requires_an_account(self):
        with self.assertRaises(SmarterValueError):
            self.run_command("deploy_llmclient", name=self.llmclient.name)

    def test_unknown_account(self):
        with self.assertRaises(SystemExit):
            self.run_command("deploy_llmclient", account_number="0000-0000-0000", name=self.llmclient.name)
        with self.assertRaises(SystemExit):
            self.run_command("deploy_llmclient", company_name=f"no such company {self.hash_suffix}", name="x")

    def test_unknown_llmclient(self):
        with patch.object(LLMClient, "save", autospec=True) as save:
            with self.assertRaises(SystemExit):
                self.run_command(
                    "deploy_llmclient", account_number=self.account.account_number, name="not_an_llmclient"
                )
        save.assert_not_called()


class TestUndeployLLMClient(DeploymentCommandTestBase):
    """Test manage.py undeploy_llmclient."""

    def setUp(self):
        super().setUp()
        self.llmclient = self.create_llmclient(f"test_undeploy_cmd_{self.hash_suffix}", deployed=True)
        patcher = patch(f"{COMMANDS}.undeploy_llmclient.undeploy_default_api")
        self.undeploy_default_api = patcher.start()
        self.addCleanup(patcher.stop)

    def test_undeploy_in_foreground(self):
        output = self.run_command(
            "undeploy_llmclient", account_number=self.account.account_number, name=self.llmclient.name, foreground=True
        )
        self.undeploy_default_api.assert_called_once_with(llmclient_id=self.llmclient.pk)
        self.undeploy_default_api.delay.assert_not_called()
        self.assertNotIn("Celery task", output)

    def test_undeploy_as_celery_task(self):
        output = self.run_command(
            "undeploy_llmclient", account_number=self.account.account_number, name=self.llmclient.name
        )
        self.undeploy_default_api.delay.assert_called_once_with(llmclient_id=self.llmclient.pk)
        self.undeploy_default_api.assert_not_called()
        self.assertIn("Celery task", output)

    def test_not_deployed(self):
        LLMClient.objects.filter(pk=self.llmclient.pk).update(
            deployed=False, dns_verification_status=LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED
        )
        self.run_command("undeploy_llmclient", account_number=self.account.account_number, name=self.llmclient.name)
        self.undeploy_default_api.assert_not_called()
        self.undeploy_default_api.delay.assert_not_called()

    def test_bad_arguments(self):
        self.run_command("undeploy_llmclient", name=self.llmclient.name)
        self.run_command("undeploy_llmclient", account_number="0000-0000-0000", name=self.llmclient.name)
        with self.assertRaises(SystemExit):
            self.run_command("undeploy_llmclient", company_name=f"no such company {self.hash_suffix}", name="x")
        with self.assertRaises(SystemExit):
            self.run_command("undeploy_llmclient", account_number=self.account.account_number, name="not_an_llmclient")
        self.undeploy_default_api.assert_not_called()
        self.undeploy_default_api.delay.assert_not_called()


class TestDeployExampleLLMClient(DeploymentCommandTestBase):
    """Test manage.py deploy_example_llmclient, against the test account rather than the Smarter account, so that the real demo llmclient is not modified."""

    def setUp(self):
        super().setUp()
        self.addCleanup(
            LLMClient.objects.filter(user_profile__account=self.account, name=SMARTER_EXAMPLE_LLM_CLIENT_NAME).delete
        )

    def test_deploy_example_llmclient(self):
        """In the background, the llmclient is saved with asynchronous=True, which sends no deployment signals."""
        self.run_command("deploy_example_llmclient", account_number=self.account.account_number)
        llmclient = LLMClient.objects.get(user_profile__account=self.account, name=SMARTER_EXAMPLE_LLM_CLIENT_NAME)
        self.assertTrue(llmclient.deployed)
        self.assertEqual(llmclient.app_name, "Smarter Demo")
        self.assertEqual(len(llmclient.app_example_prompts), 3)

    def test_deploy_example_llmclient_in_foreground(self):
        with patch.object(LLMClient, "save", autospec=True) as save:
            with patch.object(LLMClient.objects, "get_or_create") as get_or_create:
                llmclient = LLMClient(name=SMARTER_EXAMPLE_LLM_CLIENT_NAME, user_profile=self.user_profile)
                get_or_create.return_value = (llmclient, True)
                self.run_command(
                    "deploy_example_llmclient", account_number=self.account.account_number, foreground=True
                )
        self.assertTrue(llmclient.deployed)
        # once to configure the llmclient, and once, synchronously, to deploy it.
        self.assertEqual(save.call_count, 2)
        self.assertEqual(save.call_args.kwargs, {})

    def test_unknown_account(self):
        self.run_command("deploy_example_llmclient", account_number="0000-0000-0000")
        self.assertFalse(
            LLMClient.objects.filter(user_profile__account=self.account, name=SMARTER_EXAMPLE_LLM_CLIENT_NAME).exists()
        )


class TestCustomDomainCommands(DeploymentCommandTestBase):
    """Test manage.py register_custom_domain and verify_custom_domain."""

    def setUp(self):
        super().setUp()
        aws_patcher = patch(f"{COMMANDS}.register_custom_domain.aws_helper")
        self.aws_helper = aws_patcher.start()
        self.addCleanup(aws_patcher.stop)
        register_patcher = patch(f"{COMMANDS}.register_custom_domain.register_custom_domain")
        self.register_custom_domain = register_patcher.start()
        self.addCleanup(register_patcher.stop)
        verify_patcher = patch(f"{COMMANDS}.verify_custom_domain.verify_custom_domain")
        self.verify_custom_domain = verify_patcher.start()
        self.addCleanup(verify_patcher.stop)
        self.domain = f"test-{self.hash_suffix}.example.com".lower()

    def test_register_when_aws_is_unavailable(self):
        self.aws_helper.ready.return_value = False
        self.run_command("register_custom_domain", self.account.account_number, self.domain)
        self.register_custom_domain.assert_not_called()

    def test_register_unknown_domain(self):
        self.aws_helper.ready.return_value = True
        self.run_command("register_custom_domain", self.account.account_number, self.domain)
        self.register_custom_domain.assert_not_called()

    def create_custom_domain(self) -> LLMClientCustomDomain:
        custom_domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile, domain_name=self.domain, aws_hosted_zone_id="ZTESTCOMMANDS"
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=custom_domain.pk).delete)
        return custom_domain

    def test_register(self):
        self.create_custom_domain()
        self.aws_helper.ready.return_value = True
        self.register_custom_domain.return_value = True
        self.aws_helper.route53.get_ns_records.return_value = ["ns-1.awsdns.com."]
        self.run_command("register_custom_domain", self.account.account_number, self.domain)
        self.register_custom_domain.assert_called_once_with(account_id=self.account.id, domain_name=self.domain)
        self.aws_helper.route53.get_ns_records.assert_called_once_with(hosted_zone_id="ZTESTCOMMANDS")

    def test_register_failure(self):
        self.create_custom_domain()
        self.aws_helper.ready.return_value = True
        self.register_custom_domain.return_value = False
        self.run_command("register_custom_domain", self.account.account_number, self.domain)
        self.aws_helper.route53.get_ns_records.assert_not_called()

    def test_verify_in_foreground(self):
        self.create_custom_domain()
        with patch(f"{COMMANDS}.verify_custom_domain.aws_helper") as aws_helper:
            self.run_command("verify_custom_domain", self.domain, foreground=True)
        self.verify_custom_domain.assert_called_once_with(
            hosted_zone_id="ZTESTCOMMANDS", sleep_interval=1800, max_attempts=48
        )
        self.verify_custom_domain.delay.assert_not_called()
        aws_helper.route53.get_ns_records.assert_called_once_with(hosted_zone_id="ZTESTCOMMANDS")

    def test_verify_as_celery_task(self):
        self.create_custom_domain()
        with patch(f"{COMMANDS}.verify_custom_domain.aws_helper"):
            self.run_command("verify_custom_domain", self.domain)
        self.verify_custom_domain.delay.assert_called_once_with(
            hosted_zone_id="ZTESTCOMMANDS", sleep_interval=1800, max_attempts=48
        )
        self.verify_custom_domain.assert_not_called()

    def test_verify_unknown_domain(self):
        with patch(f"{COMMANDS}.verify_custom_domain.aws_helper", MagicMock()):
            with self.assertRaises(SystemExit):
                self.run_command("verify_custom_domain", self.domain)
        self.verify_custom_domain.assert_not_called()
        self.verify_custom_domain.delay.assert_not_called()
        self.assertFalse(LLMClientCustomDomain.objects.filter(domain_name=self.domain).exists())
