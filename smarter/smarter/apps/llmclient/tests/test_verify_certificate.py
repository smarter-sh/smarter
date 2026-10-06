"""
Test :mod:`smarter.apps.llmclient.tasks.verify_certificate`.

The task is called directly, which runs it synchronously. AWS ACM is mocked.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.llmclient.tasks.verify_certificate import verify_certificate
from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.verify_certificate"
CERTIFICATE_ARN = "arn:aws:acm:us-east-1:000000000000:certificate/test"


class TestVerifyCertificate(SmarterTestBase):
    """Test that an ACM certificate is verified."""

    def setUp(self):
        super().setUp()
        self.aws_helper = MagicMock()
        self.aws_helper.acm = MagicMock(spec=AWSCertificateManager)
        for target, value in (("is_taskable", MagicMock(return_value=True)), ("aws_helper", self.aws_helper)):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def test_not_taskable(self):
        self.is_taskable.return_value = False
        self.assertIsNone(verify_certificate(CERTIFICATE_ARN))
        self.aws_helper.acm.verify_certificate.assert_not_called()

    def test_acm_not_available(self):
        self.aws_helper.acm = None
        self.assertFalse(verify_certificate(CERTIFICATE_ARN))

    def test_verified_and_not_verified(self):
        """Test that the certificate is verified, whatever the result."""
        for verified in (True, False):
            with self.subTest(verified=verified):
                self.aws_helper.acm.verify_certificate.reset_mock()
                self.aws_helper.acm.verify_certificate.return_value = verified
                verify_certificate(CERTIFICATE_ARN)
                self.aws_helper.acm.verify_certificate.assert_called_once_with(certificate_arn=CERTIFICATE_ARN)
