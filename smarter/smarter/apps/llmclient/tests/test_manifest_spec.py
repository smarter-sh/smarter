"""Test the LLMClient manifest's spec.config: allowedOrigins."""

from pydantic import ValidationError

from smarter.apps.llmclient.manifest.models.llmclient.spec import SAMLLMClientSpecConfig
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestLLMClientSpecConfigAllowedOrigins(SmarterTestBase):
    """Test the validation and normalization of spec.config.allowedOrigins."""

    def test_default_is_empty(self):
        self.assertEqual(SAMLLMClientSpecConfig().allowedOrigins, [])

    def test_origins_are_normalized(self):
        config = SAMLLMClientSpecConfig(
            allowedOrigins=["HTTPS://WWW.Example.com/", "http://localhost:5173", "https://www.example.com"]
        )
        self.assertEqual(config.allowedOrigins, ["https://www.example.com", "http://localhost:5173"])

    def test_none_is_empty(self):
        self.assertEqual(SAMLLMClientSpecConfig(allowedOrigins=None).allowedOrigins, [])

    def test_invalid_origins(self):
        for origin in (
            "*",
            "https://*.example.com",
            "www.example.com",
            "ftp://example.com",
            "https://www.example.com/path",
            "https://www.example.com?x=1",
            "https://-bad.example.com",
        ):
            with self.subTest(origin=origin):
                with self.assertRaises(ValidationError):
                    SAMLLMClientSpecConfig(allowedOrigins=[origin])
