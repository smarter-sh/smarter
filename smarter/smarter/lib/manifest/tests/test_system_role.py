"""Test :mod:`smarter.lib.manifest.system_role`, and the system roles of the LLMClient and plugin manifests."""

from unittest.mock import patch

from pydantic import ValidationError

from smarter.apps.llmclient.manifest.models.llmclient.spec import (
    SAMLLMClientSpecConfigPrompt,
)
from smarter.apps.llmtool.manifest.models.common.plugin.spec import (
    SAMPluginCommonSpecPrompt,
)
from smarter.lib.manifest import system_role
from smarter.lib.manifest.system_role import (
    SMARTER_LONG_SYSTEM_ROLE_LENGTH,
    SMARTER_MAX_SYSTEM_ROLE_LENGTH,
    warn_if_long_system_role,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

LONG = "a" * (SMARTER_LONG_SYSTEM_ROLE_LENGTH + 1)
LONGEST = "a" * SMARTER_MAX_SYSTEM_ROLE_LENGTH
TOO_LONG = "a" * (SMARTER_MAX_SYSTEM_ROLE_LENGTH + 1)


class TestSystemRole(SmarterTestBase):
    """A system role may be long, is logged when it is unusually long, and is rejected only when absurdly long."""

    def test_warning(self):
        with patch.object(system_role, "logger") as logger:
            self.assertEqual(warn_if_long_system_role("short", "field"), "short")
            logger.warning.assert_not_called()
            self.assertEqual(warn_if_long_system_role(LONG, "field"), LONG)
            logger.warning.assert_called_once()

    def test_llmclient_default_system_role(self):
        with patch.object(system_role, "logger") as logger:
            self.assertIsNone(SAMLLMClientSpecConfigPrompt(defaultSystemRole=None).defaultSystemRole)
            self.assertEqual(SAMLLMClientSpecConfigPrompt(defaultSystemRole=LONGEST).defaultSystemRole, LONGEST)
        logger.warning.assert_called_once()
        with self.assertRaises(ValidationError):
            SAMLLMClientSpecConfigPrompt(defaultSystemRole=TOO_LONG)

    def test_plugin_system_role(self):
        prompt = {"provider": "openai", "model": "gpt-6-luna", "temperature": 1.0, "maxTokens": 256}
        with patch.object(system_role, "logger") as logger:
            # a system role with punctuation, and one without, are both checked.
            self.assertEqual(
                SAMPluginCommonSpecPrompt(systemRole="Hello, world!", **prompt).systemRole, "Hello, world!"
            )
            self.assertEqual(SAMPluginCommonSpecPrompt(systemRole=LONGEST, **prompt).systemRole, LONGEST)
        logger.warning.assert_called_once()
        for value in (TOO_LONG, TOO_LONG[:-1] + "!"):
            with self.subTest(clean=value.isalnum()), self.assertRaises(ValidationError):
                SAMPluginCommonSpecPrompt(systemRole=value, **prompt)

    def test_schema_publishes_the_maximum(self):
        for model, field in (
            (SAMLLMClientSpecConfigPrompt, "defaultSystemRole"),
            (SAMPluginCommonSpecPrompt, "systemRole"),
        ):
            with self.subTest(model=model.__name__):
                schema = model.model_json_schema()["properties"][field]
                lengths = [schema.get("maxLength")] + [branch.get("maxLength") for branch in schema.get("anyOf", [])]
                self.assertIn(SMARTER_MAX_SYSTEM_ROLE_LENGTH, lengths)
