"""
Test :mod:`smarter.apps.llmclient.tasks.register_custom_domain`.

The task is called directly, which runs it synchronously. The infrastructure services are mocked, and the tasks
it queues are patched, so nothing reaches the cloud or a worker.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.exceptions import (
    CertificateTimeout,
    DNSRecordTimeout,
)
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.tasks.register_custom_domain import (
    register_custom_domain,
)

MODULE = "smarter.apps.llmclient.tasks.register_custom_domain"


class TestRegisterCustomDomain(TestAccountMixin):
    """Registering a custom domain looks once for its validation records, and queues itself again rather than sleep."""

    infrastructure: MagicMock
    verify: MagicMock
    again: MagicMock

    def setUp(self):
        super().setUp()
        self.domain_name = f"test-register-{self.hash_suffix}.example.com"
        self.addCleanup(LLMClientCustomDomain.objects.filter(domain_name=self.domain_name).delete)
        self.infrastructure = MagicMock()
        self.infrastructure.dns.resolve_domain.side_effect = lambda name: name
        self.infrastructure.dns.get_or_create_zone.return_value = (MagicMock(id="Z0000000000REGISTER"), True)
        self.infrastructure.dns.record_wait_seconds = 15
        self.infrastructure.certificates.get_or_create_certificate.return_value = ("arn:register", True)
        self.infrastructure.certificates.validation_wait_attempts = 120
        self.infrastructure.certificates.validation_wait_seconds = 5
        patchers = (
            patch(f"{MODULE}.is_taskable", return_value=True),
            patch(f"{MODULE}.infrastructure", self.infrastructure),
            patch(f"{MODULE}.get_cached_admin_user_for_account", return_value=self.admin_user),
            patch(f"{MODULE}.UserProfile.get_cached_object", return_value=self.user_profile),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        verify_patcher = patch(f"{MODULE}.verify_custom_domain.delay")
        self.verify = verify_patcher.start()
        self.addCleanup(verify_patcher.stop)
        again_patcher = patch.object(register_custom_domain, "apply_async")
        self.again = again_patcher.start()
        self.addCleanup(again_patcher.stop)

    def register(self, attempt: int = 1):
        return register_custom_domain(self.account.pk, self.domain_name, attempt=attempt)

    def test_registers_and_queues_the_verification(self):
        self.assertTrue(self.register())
        certificates = self.infrastructure.certificates
        certificates.create_validation_records.assert_called_once_with("arn:register", max_attempts=1)
        custom_domain = LLMClientCustomDomain.objects.get(domain_name=self.domain_name)
        self.assertEqual(custom_domain.aws_hosted_zone_id, "Z0000000000REGISTER")
        self.verify.assert_called_once_with(hosted_zone_id="Z0000000000REGISTER")
        self.again.assert_not_called()

    def test_records_not_ready_are_looked_for_again(self):
        """Each wait that isn't over queues the next look, with its own service's interval."""
        certificates = self.infrastructure.certificates
        for error, countdown in ((CertificateTimeout("not generated"), 5), (DNSRecordTimeout("not in the zone"), 15)):
            with self.subTest(error=type(error).__name__):
                self.again.reset_mock()
                # a new domain each time: an existing one, with an issued certificate, is already registered.
                LLMClientCustomDomain.objects.filter(domain_name=self.domain_name).delete()
                certificates.create_validation_records.side_effect = error
                self.assertIsNone(self.register(attempt=3))
                self.again.assert_called_once()
                self.assertEqual(self.again.call_args.kwargs["countdown"], countdown)
                self.assertEqual(self.again.call_args.kwargs["kwargs"]["attempt"], 4)
        self.verify.assert_not_called()

    def test_out_of_attempts_fails_as_before(self):
        self.infrastructure.certificates.create_validation_records.side_effect = CertificateTimeout("not generated")
        with self.assertRaises(CertificateTimeout):
            self.register(attempt=120)
        self.again.assert_not_called()
