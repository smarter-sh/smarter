"""
The vendor's model quirks, surveyed live: real, billed requests to OpenAI's v1/chat/completions.

These tests are tagged ``vendor`` and skipped unless they are asked for, since every run sends a
few hundred small requests (a few cents) with the OpenAI api key of the environment:

.. code-block:: console

    docker exec smarter-api bash -c "cd /home/smarter_user/smarter && \\
        python manage.py test smarter.apps.provider.tests.test_vendor_quirks_live --tag vendor"

Run them when a model is added to ``VALID_CHAT_COMPLETION_MODELS``, before a release, or when a
prompt fails with a 400 from the vendor. They check that:

- the capability table, :mod:`smarter.lib.openai.model_capabilities`, still describes the models:
  each request shape is accepted or rejected, for the same parameter, as the table predicts. A
  failure means the vendor changed a model's rules: update the table, then run
  ``test_vendor_quirks.py``, which shows what Smarter must change.
- every model answers every kind of request that Smarter sends, through the chat provider's own code.
"""

import os
from unittest.mock import MagicMock

import openai
from django.test import tag
from openai.types.chat import ChatCompletion

from smarter.apps.provider.services.text_completion.const import (
    VALID_CHAT_COMPLETION_MODELS,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.apps.provider.tests.vendor_profiles import simulate
from smarter.lib.openai.model_quirks import rejected_parameter
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.runner import VENDOR

API_KEY_ENVIRONMENT_VARIABLE = "OPENAI_API_KEY"
MAX_COMPLETION_TOKENS = 32
"""Enough for the vendor to accept or reject a request.

An answer cut short is still accepted.
"""
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "The current time.",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]
SHAPES: dict[str, SmarterDictType] = {
    "custom temperature": {"temperature": 0.2},
    "default temperature": {"temperature": 1.0},
    "tools": {"tools": TOOLS, "tool_choice": "auto"},
    "tools, effort none": {"tools": TOOLS, "tool_choice": "auto", "reasoning_effort": "none"},
    "tools, effort none, custom temperature": {
        "tools": TOOLS,
        "tool_choice": "auto",
        "reasoning_effort": "none",
        "temperature": 0.2,
    },
    "effort none, custom temperature": {"reasoning_effort": "none", "temperature": 0.2},
    "effort low, custom temperature": {"reasoning_effort": "low", "temperature": 0.2},
    "tools, effort low": {"tools": TOOLS, "tool_choice": "auto", "reasoning_effort": "low"},
    "effort minimal": {"reasoning_effort": "minimal"},
    "tools, parallel_tool_calls": {"tools": TOOLS, "tool_choice": "auto", "parallel_tool_calls": False},
}
"""The request shapes of the survey: the parameters that the models disagree about."""


def outcome(error: openai.APIStatusError | None) -> str:
    """'accepted', or the parameter that the vendor rejected, e.g. 'rejected temperature'."""
    if error is None:
        return "accepted"
    parameter = rejected_parameter(error)
    return f"rejected {parameter} ({error.status_code})"


@tag(VENDOR)
class TestVendorQuirksLive(SmarterTestBase):
    """Survey the vendor's models with real requests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        api_key = os.environ.get(API_KEY_ENVIRONMENT_VARIABLE)
        if not api_key:
            raise cls.failureException(f"the vendor tests need {API_KEY_ENVIRONMENT_VARIABLE}")
        cls.client = openai.OpenAI(api_key=api_key)

    def send(self, request: SmarterDictType) -> openai.APIStatusError | None:
        """Send a request to the vendor, and return its error, if any."""
        try:
            self.client.chat.completions.create(**request)
        except openai.APIStatusError as e:
            return e
        return None

    def test_profiles_describe_the_models(self):
        """Every request shape is accepted or rejected as the model's profile predicts."""
        for model in VALID_CHAT_COMPLETION_MODELS:
            for shape, parameters in SHAPES.items():
                request = {
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_completion_tokens": MAX_COMPLETION_TOKENS,
                    **parameters,
                }
                with self.subTest(model=model, shape=shape):
                    actual = outcome(self.send(request))
                    predicted = outcome(simulate(request))
                    self.assertEqual(
                        actual, predicted, f"{model} changed: update it in smarter.lib.openai.model_capabilities"
                    )

    def test_every_model_answers_smarters_requests(self):
        """Every model answers Smarter's requests, with and without tools, through the chat provider."""
        original_api_key = openai.api_key
        original_base_url = openai.base_url
        openai.api_key = self.client.api_key
        openai.base_url = "https://api.openai.com/v1/"
        self.addCleanup(setattr, openai, "api_key", original_api_key)
        self.addCleanup(setattr, openai, "base_url", original_base_url)

        provider = OpenAISmarterClient.__new__(OpenAISmarterClient)
        provider.append_message = MagicMock()
        for model in VALID_CHAT_COMPLETION_MODELS:
            for tools in (False, True):
                with self.subTest(model=model, tools=tools):
                    provider.model = model
                    provider.model_warnings = set()
                    request = {
                        "model": model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "temperature": 0.2,
                        "max_completion_tokens": MAX_COMPLETION_TOKENS,
                    }
                    if tools:
                        request["tools"] = TOOLS
                        request["tool_choice"] = "auto"
                        response = provider.create_first_completion(request)
                    else:
                        response = provider.create_completion(request)
                    self.assertIsInstance(response, ChatCompletion)
