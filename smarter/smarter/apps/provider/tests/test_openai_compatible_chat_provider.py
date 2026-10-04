"""
Test :meth:`OpenAISmarterClient.create_first_completion`: how the first request sets reasoning_effort.

Some reasoning models, such as gpt-6-luna, reject function tools on v1/chat/completions unless
reasoning_effort is 'none'. The openai client is mocked, so no request leaves the test.
"""

from unittest.mock import MagicMock, patch

import httpx
import openai

from smarter.apps.provider.services.text_completion.lib import (
    openai_compatible_chat_provider as module,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    REASONING_EFFORT_NONE,
    OpenAISmarterClient,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

CREATE_PATCH = (
    "smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.openai.chat.completions.create"
)
TOOLS = [{"type": "function", "function": {"name": "get_current_weather", "parameters": {}}}]
UNKNOWN_MODEL = "test-reasoning-model"


def bad_request(param: str) -> openai.BadRequestError:
    """A 400 from OpenAI that names the rejected parameter."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    body = {"message": "rejected", "type": "invalid_request_error", "param": param, "code": None}
    return openai.BadRequestError("rejected", response=response, body=body)


class TestCreateFirstCompletion(SmarterTestBase):
    """Test that reasoning_effort is 'none' only when a model needs it for function tools."""

    def setUp(self):
        super().setUp()
        # the handler's other state is not needed to send the first request
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        models = patch.object(module, "TOOLS_REQUIRE_NO_REASONING_MODELS", {"gpt-6-luna"})
        models.start()
        self.addCleanup(models.stop)

    def kwargs(self, model: str, tools: bool = True) -> dict:
        self.client.model = model
        kwargs = {"model": model, "messages": [{"role": "user", "content": "hi"}]}
        if tools:
            kwargs["tools"] = TOOLS
        return kwargs

    def test_known_model_with_tools_sends_none(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(self.kwargs("gpt-6-luna"))
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["reasoning_effort"], REASONING_EFFORT_NONE)

    def test_known_model_without_tools_keeps_default(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(self.kwargs("gpt-6-luna", tools=False))
        self.assertNotIn("reasoning_effort", create.call_args.kwargs)

    def test_other_model_with_tools_omits_reasoning_effort(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(self.kwargs("gpt-4o-mini"))
        self.assertNotIn("reasoning_effort", create.call_args.kwargs)

    def test_unknown_model_is_retried_and_remembered(self):
        response = MagicMock()
        with patch(CREATE_PATCH, side_effect=[bad_request("reasoning_effort"), response]) as create:
            result = self.client.create_first_completion(self.kwargs(UNKNOWN_MODEL))
        self.assertIs(result, response)
        self.assertEqual(create.call_count, 2)
        self.assertEqual(create.call_args.kwargs["reasoning_effort"], REASONING_EFFORT_NONE)
        self.assertIn(UNKNOWN_MODEL, module.TOOLS_REQUIRE_NO_REASONING_MODELS)

        # the next request sends 'none' up front
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(self.kwargs(UNKNOWN_MODEL))
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["reasoning_effort"], REASONING_EFFORT_NONE)

    def test_other_bad_request_is_not_retried(self):
        with patch(CREATE_PATCH, side_effect=bad_request("temperature")) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_first_completion(self.kwargs(UNKNOWN_MODEL))
        create.assert_called_once()
        self.assertNotIn(UNKNOWN_MODEL, module.TOOLS_REQUIRE_NO_REASONING_MODELS)

    def test_rejection_with_none_already_sent_is_not_retried(self):
        with patch(CREATE_PATCH, side_effect=bad_request("reasoning_effort")) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_first_completion(self.kwargs("gpt-6-luna"))
        create.assert_called_once()
