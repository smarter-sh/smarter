"""
Boundary tests of the vendor's model quirks: every kind of request that Smarter sends, to every model, against a simulator of the vendor.

Each request goes through the chat provider's own code (``create_first_completion()`` and
``create_completion()``, with :func:`~smarter.lib.openai.model_quirks.apply_model_quirks` and its
retries), and ``openai.chat.completions.create()`` is answered by
:func:`~smarter.apps.provider.tests.vendor_profiles.simulate`, which rejects what the real model
rejects, with the vendor's own errors. For every model, with and without tools, at a custom and at
the default temperature, the tests check that:

- the LLM answers: no prompt fails because of a parameter that Smarter chose.
- the model sets that Smarter starts with are right: the first request is accepted.
- a process that starts knowing nothing learns, and its next request is accepted at once.
- Smarter leaves nothing out that the model would have accepted: tools, or a custom temperature.

No request leaves the process. ``test_vendor_quirks_live.py`` checks the platform's capability
table, which the simulator enforces, against the real api.
"""

import copy
from contextlib import ExitStack
from typing import Optional
from unittest.mock import patch

from openai.types.chat import ChatCompletion

from smarter.apps.provider.services.text_completion.const import (
    VALID_CHAT_COMPLETION_MODELS,
)
from smarter.apps.provider.services.text_completion.lib import (
    openai_compatible_chat_provider as module,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.apps.provider.tests.vendor_profiles import (
    PROFILES,
    accepts_tools,
    simulate,
)
from smarter.lib.openai import model_quirks
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

CREATE_PATCH = (
    "smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.openai.chat.completions.create"
)
MODEL_SETS = (
    "DEFAULT_TEMPERATURE_ONLY_MODELS",
    "SUPPORTED_REASONING_EFFORTS",
    "TOOLS_REJECT_REASONING_EFFORT_MODELS",
    "TOOLS_REQUIRE_NO_REASONING_MODELS",
    "TOOLS_UNSUPPORTED_MODELS",
)
REASONING_EFFORTS = (None, "none", "minimal", "high")
"""The LLMClient's defaultReasoningEffort: unset, no reasoning, one that no model supports, and a high one."""
TOOLS = [{"type": "function", "function": {"name": "get_current_weather", "parameters": {}}}]
CUSTOM_TEMPERATURE = 0.2
DEFAULT_TEMPERATURE = 1.0
MAX_COLD_REQUESTS = 4
"""The most requests that a prompt may take while a process learns a model's quirks."""


def completion(model: str) -> ChatCompletion:
    """A ChatCompletion, as the vendor answers an accepted request."""
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-vendor",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi"}}],
        }
    )


class FakeVendor:
    """``openai.chat.completions.create()``, answered by the simulator, recording every request."""

    def __init__(self):
        self.requests: list[SmarterDictType] = []

    def create(self, **kwargs) -> ChatCompletion:
        """Accept the request, or raise the vendor's error."""
        request = copy.deepcopy(kwargs)
        self.requests.append(request)
        error = simulate(request)
        if error is not None:
            raise error
        response = completion(str(request["model"]))
        return response


class TestVendorProfiles(SmarterTestBase):
    """Test that every model that Smarter offers is in the capability table, which the simulator enforces."""

    def test_every_valid_model_has_a_profile(self):
        missing = []
        for model in VALID_CHAT_COMPLETION_MODELS:
            if model not in PROFILES:
                missing.append(model)
        self.assertEqual(
            missing, [], "add these models to smarter.lib.openai.model_capabilities.OPENAI_MODEL_CAPABILITIES"
        )

    def test_no_profile_of_a_model_that_smarter_does_not_offer(self):
        extra = []
        for model in PROFILES:
            if model not in VALID_CHAT_COMPLETION_MODELS:
                extra.append(model)
        self.assertEqual(extra, [])


class TestVendorQuirks(SmarterTestBase):
    """Send every kind of request that Smarter sends to every model, against the simulated vendor."""

    def setUp(self):
        super().setUp()
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        patcher = patch.object(self.client, "append_message")
        self.append_message = patcher.start()
        self.addCleanup(patcher.stop)
        self.client.prompt = None

    def model_sets(self, seeded: bool) -> ExitStack:
        """
        Replace the model sets with copies, for one scenario.

        :param seeded: True for the sets that Smarter starts with, False for empty sets, as in a
            process that knows nothing yet.
        """
        stack = ExitStack()
        for name in MODEL_SETS:
            original = getattr(model_quirks, name)
            models = type(original)()
            if seeded:
                models = copy.copy(original)
            for target in (module, model_quirks):
                stack.enter_context(patch.object(target, name, models))
        return stack

    def request(self, model: str, temperature: float, tools: bool, effort: Optional[str]) -> SmarterDictType:
        """A request body as the handler builds it."""
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": temperature,
            "max_completion_tokens": 64,
        }
        if effort is not None:
            body["reasoning_effort"] = effort
        if tools:
            body["tools"] = copy.deepcopy(TOOLS)
            body["tool_choice"] = "auto"
        return body

    def send(
        self, vendor: FakeVendor, model: str, temperature: float, tools: bool, effort: Optional[str] = None
    ) -> ChatCompletion:
        """Send one request through the chat provider, as the handler does."""
        self.client.model = model
        self.client.model_warnings = set()
        self.client.reasoning_effort = effort
        body = self.request(model, temperature, tools, effort)
        with patch(CREATE_PATCH, side_effect=vendor.create):
            if tools:
                return self.client.create_first_completion(body)
            return self.client.create_completion(body)

    def assert_nothing_needless_left_out(
        self,
        model: str,
        temperature: float,
        tools: bool,
        accepted: SmarterDictType,
        effort: Optional[str] = None,
    ):
        """Assert that the accepted request has the tools, the reasoning effort and the custom temperature, if the model accepts them."""
        if tools and accepts_tools(model):
            self.assertIn("tools", accepted, f"{model} accepts tools, but they were left out")
        if effort is not None and accepted.get("reasoning_effort") != effort:
            with_effort = dict(accepted)
            with_effort["reasoning_effort"] = effort
            error = simulate(with_effort)
            self.assertIsNotNone(
                error, f"{model} accepts reasoning_effort={effort} in this request, but it was changed"
            )
        if temperature != CUSTOM_TEMPERATURE:
            return
        if "temperature" in accepted:
            return
        with_temperature = dict(accepted)
        with_temperature["temperature"] = temperature
        error = simulate(with_temperature)
        self.assertIsNotNone(error, f"{model} accepts temperature={temperature} in this request, but it was left out")

    def scenarios(self):
        """Every model, with and without tools, at a custom and at the default temperature, and at every kind of reasoning effort."""
        for model in VALID_CHAT_COMPLETION_MODELS:
            for tools in (False, True):
                for temperature in (CUSTOM_TEMPERATURE, DEFAULT_TEMPERATURE):
                    for effort in REASONING_EFFORTS:
                        yield model, tools, temperature, effort

    def test_smarters_model_sets_are_right(self):
        """With the sets that Smarter starts with, every request is accepted the first time."""
        for model, tools, temperature, effort in self.scenarios():
            with (
                self.subTest(model=model, tools=tools, temperature=temperature, effort=effort),
                self.model_sets(seeded=True),
            ):
                vendor = FakeVendor()
                response = self.send(vendor, model, temperature, tools, effort)
                self.assertIsInstance(response, ChatCompletion)
                self.assertEqual(len(vendor.requests), 1, f"rejected: {vendor.requests[:-1]}")
                self.assert_nothing_needless_left_out(model, temperature, tools, vendor.requests[-1], effort)

    def test_a_process_that_knows_nothing_learns(self):
        """With empty sets, every prompt is answered, and the next request is accepted the first time."""
        for model, tools, temperature, effort in self.scenarios():
            with (
                self.subTest(model=model, tools=tools, temperature=temperature, effort=effort),
                self.model_sets(seeded=False),
            ):
                vendor = FakeVendor()
                response = self.send(vendor, model, temperature, tools, effort)
                self.assertIsInstance(response, ChatCompletion)
                self.assertLessEqual(len(vendor.requests), MAX_COLD_REQUESTS)

                vendor = FakeVendor()
                response = self.send(vendor, model, temperature, tools, effort)
                self.assertIsInstance(response, ChatCompletion)
                self.assertEqual(len(vendor.requests), 1, f"not learned: {vendor.requests[:-1]}")
                self.assert_nothing_needless_left_out(model, temperature, tools, vendor.requests[-1], effort)

    def test_final_answer_after_tool_calls(self):
        """The final answer after tool calls is sent without tools, and is accepted the first time."""
        for model in VALID_CHAT_COMPLETION_MODELS:
            with self.subTest(model=model), self.model_sets(seeded=True):
                vendor = FakeVendor()
                self.send(vendor, model, CUSTOM_TEMPERATURE, tools=True)
                vendor = FakeVendor()
                response = self.send(vendor, model, CUSTOM_TEMPERATURE, tools=False)
                self.assertIsInstance(response, ChatCompletion)
                self.assertEqual(len(vendor.requests), 1)

    def test_tools_are_left_out_only_with_a_warning(self):
        """A model that can't use tools answers without them, and the sandbox gets a warning."""
        for model in VALID_CHAT_COMPLETION_MODELS:
            if accepts_tools(model):
                continue
            with self.subTest(model=model), self.model_sets(seeded=True):
                self.append_message.reset_mock()
                vendor = FakeVendor()
                self.send(vendor, model, CUSTOM_TEMPERATURE, tools=True)
                self.assertNotIn("tools", vendor.requests[-1])
                warnings = [call.kwargs["content"] for call in self.append_message.call_args_list]
                self.assertEqual(len(warnings), 1)
                self.assertIn("defaultModel:", warnings[0])


class TestSimulator(SmarterTestBase):
    """Test the simulator against the vendor's answers that the survey recorded."""

    def test_recorded_answers(self):
        cases: list[tuple[SmarterDictType, Optional[str]]] = [
            ({"model": "gpt-4o-mini", "reasoning_effort": "none"}, None),
            ({"model": "gpt-4o-mini", "max_tokens": 16, "temperature": 0.2}, "ok"),
            ({"model": "chat-latest", "max_tokens": 16}, "max_tokens"),
            ({"model": "chat-latest", "reasoning_effort": "low"}, "reasoning_effort"),
            ({"model": "gpt-5-search-api", "temperature": 1.0}, None),
            ({"model": "gpt-5-search-api", "tools": TOOLS}, None),
            ({"model": "gpt-5.2", "temperature": 0.2, "reasoning_effort": "low"}, "temperature"),
            ({"model": "gpt-5.2", "temperature": 0.2, "tools": TOOLS, "reasoning_effort": "low"}, "temperature"),
            ({"model": "gpt-5.4", "tools": TOOLS}, "ok"),
            ({"model": "gpt-5.4", "tools": TOOLS, "reasoning_effort": "low"}, "reasoning_effort"),
            ({"model": "gpt-5.5", "temperature": 0.2}, "temperature"),
            ({"model": "gpt-6-luna", "tools": TOOLS, "reasoning_effort": "none", "temperature": 0.2}, "ok"),
            ({"model": "gpt-6-luna", "tools": TOOLS}, "reasoning_effort"),
            ({"model": "gpt-6.1-sol", "tools": TOOLS, "reasoning_effort": "none"}, "reasoning_effort"),
            ({"model": "gpt-6.1-sol", "reasoning_effort": "high"}, "ok"),
        ]
        for request, expected in cases:
            with self.subTest(request=request):
                error = simulate(request)
                if expected == "ok":
                    self.assertIsNone(error)
                    continue
                self.assertIsNotNone(error)
                parameter = model_quirks.rejected_parameter(error)  # type: ignore[arg-type]
                if expected is None:
                    self.assertIn(parameter, ("reasoning_effort", "temperature", "tools"))
                else:
                    self.assertEqual(parameter, expected)
