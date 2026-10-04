"""
Test the verify_dns_configuration management command.

Route53 is never called: the command's aws_helper is a mock, whose route53 is a mock AWSRoute53.
"""

from unittest.mock import MagicMock, patch

from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.aws.route53 import AWSRoute53

from .base import CommandTestBase

MODULE = "smarter.apps.api.management.commands.verify_dns_configuration"
A_RECORD = {"Name": "example.com.", "Type": "A", "AliasTarget": {"DNSName": "elb.amazonaws.com."}}


def settings(environment: str) -> MagicMock:
    return MagicMock(
        environment=environment,
        aws_is_configured=True,
        root_domain="example.com",
        root_platform_domain="platform.example.com",
        root_api_domain="api.example.com",
        root_proxy_domain="proxy.example.com",
        proxy_api_domain="api.proxy.example.com",
        environment_platform_domain="alpha.platform.example.com",
        environment_api_domain="alpha.api.example.com",
        all_domains=["example.com", "api.example.com"],
    )


class TestVerifyDnsConfiguration(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.route53 = MagicMock(spec=AWSRoute53)
        self.route53.get_hosted_zone_id_for_domain.return_value = "Z1"
        self.route53.get_environment_A_record.return_value = A_RECORD
        self.route53.get_ns_records.return_value = [{"Name": "example.com."}, {"Name": "api.example.com."}]
        self.route53.get_or_create_hosted_zone.side_effect = [
            ({"Id": "/hostedzone/Z1"}, False),
            ({"Id": "/hostedzone/Z2"}, True),
        ] * 10
        self.route53.get_hosted_zone_id.return_value = "Z2"
        self.route53.get_or_create_dns_record.side_effect = [({}, True), ({}, False)] * 20
        self.route53.get_ns_records_for_domain.return_value = {"ResourceRecords": [{"Value": "ns-1."}]}
        patcher = patch(f"{MODULE}.aws_helper", MagicMock(route53=self.route53))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_in(self, environment: str) -> str:
        with patch(f"{MODULE}.smarter_settings", settings(environment)):
            return self.run_command("verify_dns_configuration")

    def test_aws_environment(self):
        """Test that every domain is verified, and delegated from its parent, in an aws environment."""
        output = self.run_in(SmarterEnvironments.ALPHA)
        self.assertIn("alpha.api.example.com", output)
        delegated = [
            c.kwargs["child_domain"]
            for c in self.route53.get_or_create_hosted_zone.call_args_list
            if "child_domain" in c.kwargs
        ]
        self.assertGreaterEqual(self.route53.get_or_create_dns_record.call_count, 12)
        self.assertEqual(delegated, [])

    def test_local_environment(self):
        output = self.run_in(SmarterEnvironments.LOCAL)
        self.assertIn("proxy.example.com", output)

    def test_aws_not_configured(self):
        local = settings(SmarterEnvironments.LOCAL)
        local.aws_is_configured = False
        with patch(f"{MODULE}.smarter_settings", local):
            self.run_command("verify_dns_configuration")
        self.route53.get_environment_A_record.assert_not_called()

    def test_missing_records(self):
        """Test that a root domain without a hosted zone or an A record fails the command."""
        self.route53.get_environment_A_record.return_value = None
        with self.assertRaises(SystemExit):
            self.run_in(SmarterEnvironments.ALPHA)
        self.route53.get_hosted_zone_id_for_domain.return_value = None
        with self.assertRaises(SystemExit):
            self.run_in(SmarterEnvironments.ALPHA)

    def test_get_any_A_record(self):  # pylint: disable=invalid-name
        from smarter.apps.api.management.commands.verify_dns_configuration import (  # pylint: disable=import-outside-toplevel
            Command,
        )

        command = Command()
        with patch(f"{MODULE}.smarter_settings", settings(SmarterEnvironments.ALPHA)):
            self.assertEqual(command.get_any_A_record(), A_RECORD)
            self.route53.get_environment_A_record.return_value = None
            with self.assertRaises(SmarterConfigurationError):
                command.get_any_A_record()

    def test_route53_not_initialized(self):
        with (
            patch(f"{MODULE}.aws_helper", MagicMock(route53=None)),
            patch(f"{MODULE}.smarter_settings", settings(SmarterEnvironments.ALPHA)),
        ):
            with self.assertRaises(SystemExit):
                self.run_command("verify_dns_configuration")
