"""
Test :mod:`smarter.apps.llmclient.tasks.verify_certificate`.

The task is called directly, which runs it synchronously. The certificate service is mocked.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.llmclient.tasks.verify_certificate import verify_certificate
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.verify_certificate"
CERTIFICATE_ARN = "arn:aws:acm:us-east-1:000000000000:certificate/test"


class TestVerifyCertificate(SmarterTestBase):
    """Test that a TLS certificate is verified."""

    def setUp(self):
        super().setUp()
        self.infrastructure = MagicMock()
        for target, value in (("is_taskable", MagicMock(return_value=True)), ("infrastructure", self.infrastructure)):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def test_not_taskable(self):
        self.is_taskable.return_value = False
        self.assertIsNone(verify_certificate(CERTIFICATE_ARN))
        self.infrastructure.certificates.wait_until_issued.assert_not_called()

    def test_verified_and_not_verified(self):
        """Test that the certificate is verified, whatever the result."""
        for verified in (True, False):
            with self.subTest(verified=verified):
                self.infrastructure.certificates.wait_until_issued.reset_mock()
                self.infrastructure.certificates.wait_until_issued.return_value = verified
                verify_certificate(CERTIFICATE_ARN)
                self.infrastructure.certificates.wait_until_issued.assert_called_once_with(CERTIFICATE_ARN)
