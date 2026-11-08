"""Test apply_model_quirks(), the rules of what OpenAI's models accept that are known before a request is sent."""

from unittest.mock import patch

import httpx
import openai

from smarter.lib.openai import model_quirks
from smarter.lib.openai.model_quirks import apply_model_quirks
from smarter.lib.unittest.base_classes import SmarterTestBase

TOOL = {"type": "function", "function": {"name": "f"}}


def model_quirks_error(message: str) -> openai.BadRequestError:
    """A 400 from OpenAI with the given message, and no param."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    body = {"message": message, "type": "invalid_request_error", "param": None, "code": None}
    return openai.BadRequestError(f"Error code: 400 - {body}", response=response, body=body)


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

    def test_tools_unsupported(self):
        """A model that can't use tools on chat completions is sent without them, and without reasoning_effort."""
        with patch.object(model_quirks, "TOOLS_UNSUPPORTED_MODELS", {"gpt-s"}):
            with patch.object(model_quirks, "TOOLS_REQUIRE_NO_REASONING_MODELS", {"gpt-s"}):
                body = {"temperature": 0.5, "tools": [TOOL], "tool_choice": "auto", "parallel_tool_calls": True}
                with_tools = apply_model_quirks(body, "gpt-s")
        self.assertEqual(with_tools, {"temperature": 0.5})

    def test_default_temperature_only(self):
        """A model that accepts only its default temperature gets none, unless the request sets reasoning_effort 'none'."""
        with patch.object(model_quirks, "DEFAULT_TEMPERATURE_ONLY_MODELS", {"gpt-t"}):
            body = apply_model_quirks({"temperature": 0.5}, "gpt-t")
            no_reasoning = apply_model_quirks({"temperature": 0.5, "reasoning_effort": "none"}, "gpt-t")
        self.assertEqual(body, {})
        self.assertEqual(no_reasoning, {"temperature": 0.5, "reasoning_effort": "none"})

    def test_reasoning_omits_temperature(self):
        """A request that reasons at an effort other than 'none' omits temperature, for every model."""
        body = apply_model_quirks({"temperature": 0.5, "reasoning_effort": "low"}, "gpt-unknown")
        self.assertEqual(body, {"reasoning_effort": "low"})

    def test_unsupported_reasoning_effort_is_left_out(self):
        with patch.object(model_quirks, "SUPPORTED_REASONING_EFFORTS", {"gpt-r": ("low", "high"), "gpt-o": ()}):
            unsupported = apply_model_quirks({"temperature": 0.5, "reasoning_effort": "minimal"}, "gpt-r")
            supported = apply_model_quirks({"reasoning_effort": "high"}, "gpt-r")
            no_reasoning = apply_model_quirks({"temperature": 0.5, "reasoning_effort": "high"}, "gpt-o")
        self.assertEqual(unsupported, {"temperature": 0.5})
        self.assertEqual(supported, {"reasoning_effort": "high"})
        self.assertEqual(no_reasoning, {"temperature": 0.5})

    def test_tools_reject_reasoning_effort(self):
        """A model that rejects tools at an explicit effort gets 'none' with tools, and keeps its default effort."""
        with patch.object(model_quirks, "TOOLS_REJECT_REASONING_EFFORT_MODELS", {"gpt-e"}):
            explicit = apply_model_quirks({"tools": [TOOL], "reasoning_effort": "high"}, "gpt-e")
            default = apply_model_quirks({"tools": [TOOL]}, "gpt-e")
            without_tools = apply_model_quirks({"reasoning_effort": "high"}, "gpt-e")
        self.assertEqual(explicit, {"tools": [TOOL], "reasoning_effort": "none"})
        self.assertEqual(default, {"tools": [TOOL]})
        self.assertEqual(without_tools, {"reasoning_effort": "high"})

    def test_supported_reasoning_efforts(self):
        """The supported values are read from the vendor's message."""
        unsupported = model_quirks_error(
            "Unsupported value: 'reasoning_effort' does not support 'none' with this model. "
            "Supported values are: 'low', 'medium', 'high', and 'xhigh'."
        )
        unrecognized = model_quirks_error("Unrecognized request argument supplied: reasoning_effort")
        tools = model_quirks_error("Function tools with reasoning_effort are not supported for gpt-x.")
        self.assertEqual(model_quirks.supported_reasoning_efforts(unsupported), ("low", "medium", "high", "xhigh"))
        self.assertEqual(model_quirks.supported_reasoning_efforts(unrecognized), ())
        self.assertIsNone(model_quirks.supported_reasoning_efforts(tools))
        self.assertTrue(model_quirks.rejects_tools_at_reasoning_effort(tools))
        self.assertFalse(model_quirks.rejects_tools_at_reasoning_effort(unsupported))
        self.assertEqual(model_quirks.rejected_parameter(unrecognized), "reasoning_effort")

    def test_applying_twice_changes_nothing_more(self):
        with (
            patch.object(model_quirks, "TOOLS_REQUIRE_NO_REASONING_MODELS", {"gpt-x"}),
            patch.object(model_quirks, "DEFAULT_TEMPERATURE_ONLY_MODELS", {"gpt-x"}),
            patch.object(model_quirks, "TOOLS_UNSUPPORTED_MODELS", set()),
            patch.object(model_quirks, "TOOLS_REJECT_REASONING_EFFORT_MODELS", set()),
            patch.object(model_quirks, "SUPPORTED_REASONING_EFFORTS", {}),
        ):
            once = apply_model_quirks({"temperature": 0.5, "tools": [TOOL]}, "gpt-x")
            twice = apply_model_quirks(dict(once), "gpt-x")
        self.assertEqual(once, twice)
        self.assertEqual(once["temperature"], 0.5)
