"""
Test :mod:`smarter.apps.llmclient.tasks.utils`.

The infrastructure services are mocked: nothing is read or applied.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.llmclient.tasks.utils import apply_ingress_manifest, is_taskable
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.utils"


class TestTaskUtils(SmarterTestBase):
    """Test is_taskable() and apply_ingress_manifest()."""

    def infrastructure(self, ready=True, dns=True, certificates=True) -> MagicMock:
        infrastructure = MagicMock()
        infrastructure.ready = ready
        infrastructure.dns.ready = dns
        infrastructure.certificates.ready = certificates
        return infrastructure

    def test_is_taskable(self):
        """Test that a request is taskable only when the provider, DNS and certificates are all ready."""
        for kwargs, expected in (
            ({}, True),
            ({"ready": False}, False),
            ({"dns": False}, False),
            ({"certificates": False}, False),
        ):
            with self.subTest(**kwargs):
                with patch(f"{MODULE}.infrastructure", self.infrastructure(**kwargs)):
                    self.assertEqual(is_taskable(), expected)

    def test_apply_ingress_manifest(self):
        """Test that the ingress manifest of a hostname is rendered and applied."""
        with patch(f"{MODULE}.infrastructure") as infrastructure:
            apply_ingress_manifest("test-llmclient.api.example.com")
        infrastructure.kubernetes.apply_manifest.assert_called_once()
        manifest = infrastructure.kubernetes.apply_manifest.call_args.args[0]
        self.assertIn("test-llmclient.api.example.com", manifest)
        self.assertNotIn("$domain", manifest)
