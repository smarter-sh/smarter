"""Test apply_model_quirks(), the rules of what OpenAI's models accept that are known before a request is sent."""

from unittest.mock import patch

from smarter.lib.openai import model_quirks
from smarter.lib.openai.model_quirks import apply_model_quirks
from smarter.lib.unittest.base_classes import SmarterTestBase

TOOL = {"type": "function", "function": {"name": "f"}}


class TestApplyModelQuirks(SmarterTestBase):
    """Test apply_model_quirks()."""

    def test_an_ordinary_model_is_unchanged(self):
        body = {"model": "gpt-test", "temperature": 0.5, "tools": [TOOL]}
        self.assertEqual(apply_model_quirks(dict(body), "gpt-test"), body)

    def test_tools_require_no_reasoning(self):
        """A model that rejects tools at its default reasoning effort gets reasoning_effort 'none', with tools only."""
        with patch.object(model_quirks, "TOOLS_REQUIRE_NO_REASONING_MODELS", {"gpt-r"}):
            with_tools = apply_model_quirks({"temperature": 0.5, "tools": [TOOL]}, "gpt-r")
            without_tools = apply_model_quirks({"temperature": 0.5}, "gpt-r")
        self.assertEqual(with_tools, {"temperature": 0.5, "tools": [TOOL], "reasoning_effort": "none"})
        self.assertEqual(without_tools, {"temperature": 0.5})

    def test_default_temperature_only(self):
        """A model that accepts only its default temperature gets none, unless the request sets reasoning_effort."""
        with patch.object(model_quirks, "DEFAULT_TEMPERATURE_ONLY_MODELS", {"gpt-t"}):
            body = apply_model_quirks({"temperature": 0.5}, "gpt-t")
            reasoning = apply_model_quirks({"temperature": 0.5, "reasoning_effort": "low"}, "gpt-t")
        self.assertEqual(body, {})
        self.assertEqual(reasoning, {"temperature": 0.5, "reasoning_effort": "low"})

    def test_applying_twice_changes_nothing_more(self):
        with (
            patch.object(model_quirks, "TOOLS_REQUIRE_NO_REASONING_MODELS", {"gpt-x"}),
            patch.object(model_quirks, "DEFAULT_TEMPERATURE_ONLY_MODELS", {"gpt-x"}),
        ):
            once = apply_model_quirks({"temperature": 0.5, "tools": [TOOL]}, "gpt-x")
            twice = apply_model_quirks(dict(once), "gpt-x")
        self.assertEqual(once, twice)
        self.assertEqual(once["temperature"], 0.5)
