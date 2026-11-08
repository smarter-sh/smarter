"""Test the capabilities of OpenAI's models, and the LLMClient settings that a model can never honor."""

from smarter.apps.provider.services.text_completion.const import (
    VALID_CHAT_COMPLETION_MODELS,
)
from smarter.lib.openai import model_quirks
from smarter.lib.openai.model_capabilities import (
    OPENAI_MODEL_CAPABILITIES,
    closest_reasoning_effort,
    llmclient_settings_errors,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestModelCapabilities(SmarterTestBase):
    """Test the capability table."""

    def test_every_valid_model_has_capabilities(self):
        missing = []
        for model in VALID_CHAT_COMPLETION_MODELS:
            if model not in OPENAI_MODEL_CAPABILITIES:
                missing.append(model)
        self.assertEqual(missing, [], "add these models to OPENAI_MODEL_CAPABILITIES")

    def test_accepts_tools(self):
        self.assertTrue(OPENAI_MODEL_CAPABILITIES["gpt-4o"].accepts_tools)
        self.assertTrue(OPENAI_MODEL_CAPABILITIES["gpt-6-luna"].accepts_tools)
        self.assertFalse(OPENAI_MODEL_CAPABILITIES["gpt-6.1-sol"].accepts_tools)
        self.assertFalse(OPENAI_MODEL_CAPABILITIES["gpt-5-search-api"].accepts_tools)

    def test_accepts_temperature(self):
        luna = OPENAI_MODEL_CAPABILITIES["gpt-6-luna"]
        self.assertTrue(luna.accepts_temperature(1.0, None))
        self.assertFalse(luna.accepts_temperature(0.2, None))
        self.assertTrue(luna.accepts_temperature(0.2, "none"))
        gpt_5_2 = OPENAI_MODEL_CAPABILITIES["gpt-5.2"]
        self.assertTrue(gpt_5_2.accepts_temperature(0.2, None))
        self.assertFalse(gpt_5_2.accepts_temperature(0.2, "high"))
        self.assertFalse(OPENAI_MODEL_CAPABILITIES["gpt-5-search-api"].accepts_temperature(1.0, None))
        self.assertFalse(OPENAI_MODEL_CAPABILITIES["chat-latest"].accepts_temperature(0.2, None))

    def test_model_quirks_start_from_the_table(self):
        self.assertIn("gpt-6.1-sol", model_quirks.TOOLS_UNSUPPORTED_MODELS)
        self.assertIn("gpt-6-luna", model_quirks.TOOLS_REQUIRE_NO_REASONING_MODELS)
        self.assertIn("gpt-5.4", model_quirks.TOOLS_REJECT_REASONING_EFFORT_MODELS)
        self.assertIn("chat-latest", model_quirks.DEFAULT_TEMPERATURE_ONLY_MODELS)
        self.assertNotIn("gpt-5.2", model_quirks.DEFAULT_TEMPERATURE_ONLY_MODELS)
        self.assertEqual(model_quirks.SUPPORTED_REASONING_EFFORTS["gpt-4o"], ())

    def test_closest_reasoning_effort(self):
        self.assertEqual(closest_reasoning_effort("minimal", ("none", "low", "high")), "low")
        self.assertEqual(closest_reasoning_effort("none", ("low", "medium")), "low")
        self.assertEqual(closest_reasoning_effort("xhigh", ("medium",)), "medium")
        self.assertEqual(closest_reasoning_effort("high", ("low", "high")), "high")


class TestLLMClientSettingsErrors(SmarterTestBase):
    """Test the LLMClient settings that a model can never honor."""

    def errors(self, model, temperature=None, reasoning_effort=None, has_tools=False) -> list[str]:
        return llmclient_settings_errors(model, temperature, reasoning_effort, has_tools)

    def test_settings_that_work(self):
        self.assertEqual(self.errors("gpt-6-luna", 1.0, None, True), [])
        self.assertEqual(self.errors("gpt-6-luna", 0.2, "none", False), [])
        self.assertEqual(self.errors("gpt-6.1-sol", 1.0, "high", False), [])
        self.assertEqual(self.errors("gpt-4o", 0.2, None, True), [])
        self.assertEqual(self.errors("gpt-5.2", 0.2, None, True), [])

    def test_models_that_are_not_checked(self):
        self.assertEqual(self.errors(None, 0.2, "minimal", True), [])
        self.assertEqual(self.errors("gemini-2.5-flash", 0.2, "minimal", True), [])

    def test_tools_on_a_model_that_cant_use_them(self):
        errors = self.errors("gpt-6.1-sol", has_tools=True)
        self.assertEqual(len(errors), 1)
        self.assertIn("defaultModel: gpt-6-luna", errors[0])

    def test_unsupported_reasoning_effort(self):
        errors = self.errors("gpt-6-luna", reasoning_effort="minimal")
        self.assertEqual(len(errors), 1)
        self.assertIn("defaultReasoningEffort: low", errors[0])

    def test_reasoning_effort_on_a_model_that_does_not_reason(self):
        errors = self.errors("gpt-4o", reasoning_effort="high")
        self.assertEqual(len(errors), 1)
        self.assertIn("doesn't reason", errors[0])

    def test_temperature_while_reasoning(self):
        errors = self.errors("gpt-5.2", 0.2, "high")
        self.assertEqual(len(errors), 1)
        self.assertIn("defaultReasoningEffort: none", errors[0])

    def test_temperature_that_is_always_ignored(self):
        errors = self.errors("gpt-6-luna", 0.2)
        self.assertEqual(len(errors), 1)
        self.assertIn("defaultReasoningEffort: none", errors[0])
        no_none = self.errors("gpt-6.1-sol", 0.2)
        self.assertEqual(len(no_none), 1)
        self.assertNotIn("defaultReasoningEffort: none", no_none[0])
        self.assertEqual(len(self.errors("gpt-5-search-api", 1.0)), 1)

    def test_temperature_that_requests_with_tools_use(self):
        """A temperature that the requests that offer tools use, at reasoning effort 'none', is allowed."""
        self.assertEqual(self.errors("gpt-6-luna", 0.2, None, True), [])

    def test_every_error_at_once(self):
        errors = self.errors("gpt-6.1-sol", 0.2, "minimal", True)
        self.assertEqual(len(errors), 3)
