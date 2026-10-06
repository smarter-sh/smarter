"""
Test :mod:`smarter.apps.llmclient.tasks.utils`.

AWS and Kubernetes are mocked: nothing is read or applied.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.llmclient.tasks.utils import apply_ingress_manifest, is_taskable
from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.common.helpers.aws.route53 import AWSRoute53
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.utils"


class TestTaskUtils(SmarterTestBase):
    """Test is_taskable() and apply_ingress_manifest()."""

    def aws_helper(self, ready=True, route53=True, acm=True) -> MagicMock:
        aws_helper = MagicMock()
        aws_helper.ready.return_value = ready
        aws_helper.route53 = MagicMock(spec=AWSRoute53) if route53 else None
        aws_helper.acm = MagicMock(spec=AWSCertificateManager) if acm else None
        return aws_helper

    def test_is_taskable(self):
        """Test that a request is taskable only when AWS, Route53 and ACM are all available."""
        for kwargs, expected in (
            ({}, True),
            ({"ready": False}, False),
            ({"route53": False}, False),
            ({"acm": False}, False),
        ):
            with self.subTest(**kwargs):
                with patch(f"{MODULE}.aws_helper", self.aws_helper(**kwargs)):
                    self.assertEqual(is_taskable(), expected)

    def test_apply_ingress_manifest(self):
        """Test that the ingress manifest of a hostname is rendered and applied."""
        with patch(f"{MODULE}.kubernetes_helper") as kubernetes_helper:
            apply_ingress_manifest("test-llmclient.api.example.com")
        kubernetes_helper.apply_manifest.assert_called_once()
        manifest = kubernetes_helper.apply_manifest.call_args.args[0]
        self.assertIn("test-llmclient.api.example.com", manifest)
        self.assertNotIn("$domain", manifest)
