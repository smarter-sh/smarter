"""
Test :class:`OpenAISmarterClient`.

- :meth:`OpenAISmarterClient.create_first_completion`: how the first request sets reasoning_effort.
  Some reasoning models, such as gpt-6-luna, reject function tools on v1/chat/completions unless
  reasoning_effort is 'none'.
- :meth:`OpenAISmarterClient.handler`: that an error response from the LLM provider is returned
  with the provider's status and message.
- :meth:`OpenAISmarterClient.handle_plugin_selected`: that a plugin does not change the LLM settings.

The openai client is mocked, so no request leaves the test.
"""

import json
import secrets
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import httpx
import openai
from pydantic import SecretStr

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.plugin.models import PluginPrompt
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
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
# Celery tasks that write rows that refer to the prompt, or charge for it. Celery is not eager in tests, so
# unpatched, they run in the live worker, which can write a row while tearDownClass deletes the prompt.
PROMPT_TASK_PATCHES = (
    "smarter.apps.prompt.receivers.create_prompt_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_tool_call_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_plugin_usage",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_charge",
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


def model_not_found(model: str) -> openai.NotFoundError:
    """A 404 from OpenAI for a model that does not exist."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(404, request=request)
    body = {
        "message": f"The model `{model}` does not exist or you do not have access to it.",
        "type": "invalid_request_error",
        "param": None,
        "code": "model_not_found",
    }
    return openai.NotFoundError("not found", response=response, body=body)


class TestHandlerProviderErrors(TestAccountMixin):
    """Test that the handler returns the LLM provider's error status and message."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for target in PROMPT_TASK_PATCHES:
            patcher = patch(target)
            patcher.start()
            cls.addClassCleanup(patcher.stop)
        cls.llmclient = LLMClient.objects.create(
            name=f"test_handler_errors_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            deployed=False,
            default_model="gpt-nonexistent-9000",
        )
        cls.prompt = Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=cls.user_profile,
            llmclient=cls.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.test.com",
        )

    @classmethod
    def tearDownClass(cls):
        cls.prompt.delete()
        cls.llmclient.delete()
        super().tearDownClass()

    def provider(self) -> OpenAISmarterClient:
        provider_orm = Provider.objects.filter(name="openai").first()
        if provider_orm is None:
            self.skipTest("the platform's openai Provider does not exist.")
        provider = OpenAISmarterClient(
            provider=provider_orm,
            provider_name="openai",
            base_url="https://api.example.com/v1/",
            api_key=SecretStr("sk-test"),
            default_model="gpt-6-luna",
        )
        provider.prompt = self.prompt
        return provider

    def test_provider_error_status_and_message(self):
        """Test that a 404 from OpenAI is returned as a 404, with OpenAI's message, for the LLMClient's model."""
        data = {
            "session_key": self.prompt.session_key,
            "messages": [{"role": "user", "content": "Hello"}],
        }
        with patch(CREATE_PATCH, side_effect=model_not_found("gpt-nonexistent-9000")) as create:
            response = self.provider().handler(self.user_profile, self.prompt, data)
        self.assertEqual(create.call_args.kwargs["model"], "gpt-nonexistent-9000")
        self.assertEqual(response["statusCode"], HTTPStatus.NOT_FOUND)
        body = json.loads(response["body"])
        self.assertEqual(body["error"]["status"], HTTPStatus.NOT_FOUND)
        self.assertEqual(
            body["error"]["message"],
            "The model `gpt-nonexistent-9000` does not exist or you do not have access to it.",
        )
        # the error is also in the message history, which the prompt engineers workbench displays
        self.assertIn("does not exist", json.dumps(body["response"]))


class TestHandlePluginSelected(SmarterTestBase):
    """Test that a selected plugin does not change the LLMClient's model, temperature or max tokens."""

    def test_plugin_does_not_change_llm_settings(self):
        client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        client.model = "llmclient-model"
        client.temperature = 0.3
        client.max_completion_tokens = 1000
        client.messages = [{"role": "user", "content": "hi"}]
        client.tools = None
        client.available_functions = {}
        plugin = MagicMock()
        plugin.plugin_prompt = MagicMock(spec=PluginPrompt, model="plugin-model", temperature=1.0)
        plugin.plugin_prompt.max_completion_tokens = 4096
        plugin.customize_prompt.side_effect = lambda messages: messages
        with patch.object(OpenAISmarterClient, "append_message_plugin_selected"):
            client.handle_plugin_selected(plugin)
        self.assertEqual(client.model, "llmclient-model")
        self.assertEqual(client.temperature, 0.3)
        self.assertEqual(client.max_completion_tokens, 1000)
        self.assertEqual(client.tools, [plugin.custom_tool])
