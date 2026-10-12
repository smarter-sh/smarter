"""Test the LLMClient manifest's spec.config: its prompt and styles, and prompt.allowedOrigins."""

from pydantic import ValidationError

from smarter.apps.llmclient.manifest.models.llmclient.spec import (
    SAMLLMClientSpecConfig,
    SAMLLMClientSpecConfigPrompt,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestLLMClientSpecConfigAllowedOrigins(SmarterTestBase):
    """Test the validation and normalization of spec.config.prompt.allowedOrigins."""

    def test_default_is_empty(self):
        self.assertEqual(SAMLLMClientSpecConfigPrompt().allowedOrigins, [])

    def test_origins_are_normalized(self):
        config = SAMLLMClientSpecConfigPrompt(
            allowedOrigins=["HTTPS://WWW.Example.com/", "http://localhost:5173", "https://www.example.com"]
        )
        self.assertEqual(config.allowedOrigins, ["https://www.example.com", "http://localhost:5173"])

    def test_none_is_empty(self):
        self.assertEqual(SAMLLMClientSpecConfigPrompt(allowedOrigins=None).allowedOrigins, [])

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
                    SAMLLMClientSpecConfigPrompt(allowedOrigins=[origin])


class TestLLMClientSpecConfig(SmarterTestBase):
    """Test spec.config, which is split into prompt and styles."""

    def test_prompt_is_required(self):
        with self.assertRaises(ValidationError):
            SAMLLMClientSpecConfig()

    def test_styles_are_optional(self):
        config = SAMLLMClientSpecConfig(prompt={"appName": "Example"})
        self.assertEqual(config.prompt.appName, "Example")
        self.assertIsNone(config.styles)

    def test_prompt_and_styles(self):
        config = SAMLLMClientSpecConfig(
            prompt={"appName": "Example"},
            styles={"appLogoUrl": "https://cdn.example.com/logo.png", "messageList": {"backgroundColor": "#fff"}},
        )
        self.assertEqual(config.styles.appLogoUrl, "https://cdn.example.com/logo.png")
        self.assertEqual(config.styles.messageList.backgroundColor, "#fff")

    def test_settings_outside_of_prompt_are_ignored(self):
        """The model ignores keys that it doesn't define. Apply rejects them, see the broker's tests."""
        with self.assertRaises(ValidationError):
            SAMLLMClientSpecConfig(appName="Example")
