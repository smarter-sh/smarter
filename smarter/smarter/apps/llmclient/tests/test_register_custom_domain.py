"""
Test :mod:`smarter.apps.llmclient.tasks.register_custom_domain`.

The task is called directly, which runs it synchronously, in this process. AWS is mocked: no
hosted zone or certificate is created, and verify_custom_domain is not queued.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.models import Account, User
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.tasks.exceptions import LLMClientCustomDomainExists
from smarter.apps.llmclient.tasks.register_custom_domain import register_custom_domain
from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.common.helpers.aws.route53 import AWSRoute53

MODULE = "smarter.apps.llmclient.tasks.register_custom_domain"
Status = LLMClientCustomDomain.VerificationStatusChoices


class TestRegisterCustomDomain(TestAccountMixin):
    """Test that registering a custom domain creates its AWS resources, and starts its verification."""

    def setUp(self):
        super().setUp()
        self.domain_name = f"test-register-{self.hash_suffix}.example.com".lower()
        self.addCleanup(LLMClientCustomDomain.objects.filter(domain_name=self.domain_name).delete)

        aws_helper = MagicMock()
        aws_helper.acm = MagicMock(spec=AWSCertificateManager)
        aws_helper.route53 = MagicMock(spec=AWSRoute53)
        aws_helper.aws.domain_resolver.side_effect = lambda domain_name: domain_name
        aws_helper.route53.get_or_create_hosted_zone.return_value = ({"Id": "ZREGISTERED"}, True)
        aws_helper.acm.get_or_create_certificate.return_value = "arn:certificate"
        for target, value in (
            ("is_taskable", MagicMock(return_value=True)),
            ("aws_helper", aws_helper),
            ("verify_custom_domain", MagicMock()),
        ):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def test_register_new_domain(self):
        """A new domain gets a hosted zone and a certificate, and its verification starts."""
        register_custom_domain(account_id=self.account.id, domain_name=self.domain_name)
        custom_domain = LLMClientCustomDomain.objects.get(domain_name=self.domain_name)
        self.assertEqual(custom_domain.aws_hosted_zone_id, "ZREGISTERED")
        self.assertEqual(custom_domain.user_profile.account, self.account)
        self.assertEqual(custom_domain.verification_status, Status.VERIFYING)
        self.aws_helper.acm.get_or_create_certificate_dns_record.assert_called_once_with(
            certificate_arn="arn:certificate"
        )
        self.verify_custom_domain.delay.assert_called_once_with(hosted_zone_id="ZREGISTERED")

    def test_register_applied_domain(self):
        """A domain applied with smarter apply is registered as it is, whoever in the account owns it."""
        applied = LLMClientCustomDomain.objects.create(
            name="applied_domain", user_profile=self.non_admin_user_profile, domain_name=self.domain_name
        )
        self.aws_helper.acm.get_certificate_arn.return_value = None
        register_custom_domain(account_id=self.account.id, domain_name=self.domain_name)
        self.assertEqual(LLMClientCustomDomain.objects.filter(domain_name=self.domain_name).count(), 1)
        applied.refresh_from_db()
        self.assertEqual(applied.aws_hosted_zone_id, "ZREGISTERED")
        self.assertEqual(applied.user_profile, self.non_admin_user_profile)
        self.verify_custom_domain.delay.assert_called_once_with(hosted_zone_id="ZREGISTERED")

    def test_registered_domain_is_verified_again(self):
        """A registered domain whose certificate is issued, but that is not verified, is verified again."""
        LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile, domain_name=self.domain_name, aws_hosted_zone_id="ZEXISTING"
        )
        self.aws_helper.acm.get_certificate_arn.return_value = "arn:certificate"
        self.aws_helper.acm.certificate_is_verified.return_value = True
        register_custom_domain(account_id=self.account.id, domain_name=self.domain_name)
        self.aws_helper.route53.get_or_create_hosted_zone.assert_not_called()
        self.verify_custom_domain.delay.assert_called_once_with(hosted_zone_id="ZEXISTING")
        self.assertEqual(
            LLMClientCustomDomain.objects.get(domain_name=self.domain_name).verification_status, Status.VERIFYING
        )

    def test_verified_domain_is_not_verified_again(self):
        custom_domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile, domain_name=self.domain_name, aws_hosted_zone_id="ZEXISTING"
        )
        custom_domain.set_verification_status(Status.VERIFIED)
        self.aws_helper.acm.get_certificate_arn.return_value = "arn:certificate"
        self.aws_helper.acm.certificate_is_verified.return_value = True
        register_custom_domain(account_id=self.account.id, domain_name=self.domain_name)
        self.verify_custom_domain.delay.assert_not_called()
        self.assertEqual(
            LLMClientCustomDomain.objects.get(domain_name=self.domain_name).verification_status, Status.VERIFIED
        )

    def test_domain_registered_by_another_account(self):
        """A domain that another account registered cannot be registered."""
        other_user, other_account, other_user_profile = admin_user_factory()
        # delete the other account's objects directly: factory_account_teardown() would also
        # sweep this class's own test account.
        self.addCleanup(User.objects.filter(pk=other_user.pk).delete)
        self.addCleanup(Account.objects.filter(pk=other_account.pk).delete)
        LLMClientCustomDomain.objects.create(
            user_profile=other_user_profile, domain_name=self.domain_name, aws_hosted_zone_id="ZOTHER"
        )
        with self.assertRaises(LLMClientCustomDomainExists):
            register_custom_domain(account_id=self.account.id, domain_name=self.domain_name)
        self.aws_helper.route53.get_or_create_hosted_zone.assert_not_called()
        self.verify_custom_domain.delay.assert_not_called()
