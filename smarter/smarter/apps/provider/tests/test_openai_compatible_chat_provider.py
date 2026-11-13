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
from unittest.mock import MagicMock, PropertyMock, patch

import httpx
import openai
from pydantic import SecretStr

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.models import PluginPrompt
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.lib import (
    openai_compatible_chat_provider as module,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    REASONING_EFFORT_NONE,
    OpenAISmarterClient,
)
from smarter.lib.openai import model_quirks
from smarter.lib.typing import SmarterDictType
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


def bad_request(param: str, message: str = "rejected") -> openai.BadRequestError:
    """A 400 from OpenAI that names the rejected parameter."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    body = {"message": message, "type": "invalid_request_error", "param": param, "code": None}
    return openai.BadRequestError(message, response=response, body=body)


def tools_at_effort() -> openai.BadRequestError:
    """OpenAI's 400 for tools at a reasoning effort other than 'none'."""
    message = (
        f"Function tools with reasoning_effort are not supported for {UNKNOWN_MODEL} in /v1/chat/completions. "
        "To use function tools, use /v1/responses or set reasoning_effort to 'none'."
    )
    return bad_request("reasoning_effort", message)


def effort_unsupported(effort: str, supported: str) -> openai.BadRequestError:
    """OpenAI's 400 for a reasoning effort that the model doesn't support."""
    message = (
        f"Unsupported value: 'reasoning_effort' does not support '{effort}' with this model. "
        f"Supported values are: {supported}."
    )
    return bad_request("reasoning_effort", message)


NO_NONE = "'low', 'medium', 'high', and 'xhigh'"


def patch_model_set(test: SmarterTestBase, name: str, models) -> None:
    """
    Replace a set of smarter.lib.openai.model_quirks for a test.

    The chat provider and apply_model_quirks() share one set, which the provider imports by name, so the
    same set replaces both.
    """
    for target in (module, model_quirks):
        patcher = patch.object(target, name, models)
        patcher.start()
        test.addCleanup(patcher.stop)


class TestCreateFirstCompletion(SmarterTestBase):
    """Test that reasoning_effort is 'none' only when a model needs it for function tools."""

    def setUp(self):
        super().setUp()
        # the handler's other state is not needed to send the first request
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        patcher = patch.object(self.client, "append_message")
        self.append_message = patcher.start()
        self.addCleanup(patcher.stop)
        patch_model_set(self, "TOOLS_REQUIRE_NO_REASONING_MODELS", {"gpt-6-luna"})
        patch_model_set(self, "TOOLS_UNSUPPORTED_MODELS", {"gpt-6.1-sol"})
        patch_model_set(self, "TOOLS_REJECT_REASONING_EFFORT_MODELS", set())
        patch_model_set(self, "SUPPORTED_REASONING_EFFORTS", {})

    def kwargs(self, model: str, tools: bool = True) -> SmarterDictType:
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
        with patch(CREATE_PATCH, side_effect=[tools_at_effort(), response]) as create:
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
        with patch(CREATE_PATCH, side_effect=bad_request("max_completion_tokens")) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_first_completion(self.kwargs(UNKNOWN_MODEL))
        create.assert_called_once()
        self.assertNotIn(UNKNOWN_MODEL, module.TOOLS_REQUIRE_NO_REASONING_MODELS)

    def test_failed_retry_is_not_remembered(self):
        """A model that rejects the retry for another reason is not remembered as needing 'none'."""
        side_effect = [tools_at_effort(), bad_request("max_completion_tokens")]
        with patch(CREATE_PATCH, side_effect=side_effect) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_first_completion(self.kwargs(UNKNOWN_MODEL))
        self.assertEqual(create.call_count, 2)
        self.assertNotIn(UNKNOWN_MODEL, module.TOOLS_REQUIRE_NO_REASONING_MODELS)

    def test_rejection_with_none_already_sent_is_sent_without_tools(self):
        """A known model that rejects 'none' too answers without its tools, and is remembered."""
        response = MagicMock()
        side_effect = [effort_unsupported("none", NO_NONE), tools_at_effort(), response]
        with patch(CREATE_PATCH, side_effect=side_effect) as create:
            result = self.client.create_first_completion(self.kwargs("gpt-6-luna"))
        self.assertIs(result, response)
        self.assertEqual(create.call_count, 3)
        self.assertNotIn("tools", create.call_args.kwargs)
        self.assertNotIn("reasoning_effort", create.call_args.kwargs)
        self.assertNotIn("gpt-6-luna", module.TOOLS_REQUIRE_NO_REASONING_MODELS)
        self.assertIn("gpt-6-luna", module.TOOLS_UNSUPPORTED_MODELS)

    def test_model_that_rejects_none_answers_without_tools(self):
        """
        A model that rejects tools at its default reasoning effort, and rejects 'none' too, as.

        gpt-6.1-sol does, answers without its tools, with a smarter message that names them.
        """
        response = MagicMock()
        kwargs = self.kwargs(UNKNOWN_MODEL)
        kwargs["tool_choice"] = "auto"
        side_effect = [tools_at_effort(), effort_unsupported("none", NO_NONE), response]
        with patch(CREATE_PATCH, side_effect=side_effect) as create:
            result = self.client.create_first_completion(kwargs)
        self.assertIs(result, response)
        self.assertEqual(create.call_count, 3)
        sent = create.call_args.kwargs
        self.assertNotIn("tools", sent)
        self.assertNotIn("tool_choice", sent)
        self.assertNotIn("reasoning_effort", sent)
        self.assertNotIn(UNKNOWN_MODEL, module.TOOLS_REQUIRE_NO_REASONING_MODELS)
        self.assertIn(UNKNOWN_MODEL, module.TOOLS_UNSUPPORTED_MODELS)
        self.append_message.assert_called_once()
        notice = self.append_message.call_args.kwargs["content"]
        self.assertIn(UNKNOWN_MODEL, notice)
        self.assertIn("get_current_weather", notice)

        # the next prompt's request leaves out its tools up front
        self.append_message.reset_mock()
        self.client.model_warnings = set()
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(self.kwargs(UNKNOWN_MODEL))
        create.assert_called_once()
        self.assertNotIn("tools", create.call_args.kwargs)
        self.append_message.assert_called_once()

    def test_known_unsupported_model_answers_without_tools(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(self.kwargs("gpt-6.1-sol"))
        create.assert_called_once()
        self.assertNotIn("tools", create.call_args.kwargs)
        self.assertNotIn("reasoning_effort", create.call_args.kwargs)
        self.append_message.assert_called_once()

    def test_known_unsupported_model_without_tools_has_no_notice(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(self.kwargs("gpt-6.1-sol", tools=False))
        create.assert_called_once()
        self.append_message.assert_not_called()

    def test_llmclient_effort_with_tools_is_retried_with_none(self):
        """A model that rejects tools at the LLMClient's effort uses 'none' with tools, and is remembered for it."""
        response = MagicMock()
        kwargs = self.kwargs(UNKNOWN_MODEL)
        kwargs["reasoning_effort"] = "high"
        with patch(CREATE_PATCH, side_effect=[tools_at_effort(), response]) as create:
            result = self.client.create_first_completion(kwargs)
        self.assertIs(result, response)
        self.assertEqual(create.call_args.kwargs["reasoning_effort"], REASONING_EFFORT_NONE)
        self.assertIn(UNKNOWN_MODEL, module.TOOLS_REJECT_REASONING_EFFORT_MODELS)
        self.assertNotIn(UNKNOWN_MODEL, module.TOOLS_REQUIRE_NO_REASONING_MODELS)

    def test_model_without_none_answers_at_the_llmclients_effort(self):
        """A model without 'none' answers without tools, at the LLMClient's own effort."""
        response = MagicMock()
        self.client.reasoning_effort = "high"
        kwargs = self.kwargs(UNKNOWN_MODEL)
        kwargs["reasoning_effort"] = "high"
        side_effect = [tools_at_effort(), effort_unsupported("none", NO_NONE), response]
        with patch(CREATE_PATCH, side_effect=side_effect) as create:
            self.client.create_first_completion(kwargs)
        self.assertEqual(create.call_count, 3)
        self.assertNotIn("tools", create.call_args.kwargs)
        self.assertEqual(create.call_args.kwargs["reasoning_effort"], "high")

    def test_reasoning_effort_set_by_the_caller_is_not_changed(self):
        kwargs = self.kwargs(UNKNOWN_MODEL)
        kwargs["reasoning_effort"] = "low"
        with patch(CREATE_PATCH, side_effect=bad_request("reasoning_effort")) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_first_completion(kwargs)
        create.assert_called_once()
        self.assertNotIn(UNKNOWN_MODEL, module.TOOLS_UNSUPPORTED_MODELS)

    def test_rejection_without_tools_is_not_retried(self):
        with patch(CREATE_PATCH, side_effect=bad_request("reasoning_effort")) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_first_completion(self.kwargs(UNKNOWN_MODEL, tools=False))
        create.assert_called_once()


class TestCreateCompletion(SmarterTestBase):
    """Test that temperature is omitted only for a model that accepts only its default temperature."""

    def setUp(self):
        super().setUp()
        # the handler's other state is not needed to send a request
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        patcher = patch.object(self.client, "append_message")
        self.append_message = patcher.start()
        self.addCleanup(patcher.stop)
        patch_model_set(self, "DEFAULT_TEMPERATURE_ONLY_MODELS", {"gpt-6-luna"})
        patch_model_set(self, "SUPPORTED_REASONING_EFFORTS", {})

    def test_unsupported_reasoning_effort_is_learned(self):
        """A rejected reasoning effort is left out, with the request's temperature, and the model's efforts are remembered."""
        response = MagicMock()
        kwargs = self.kwargs(UNKNOWN_MODEL)
        kwargs["reasoning_effort"] = "minimal"
        rejection = effort_unsupported("minimal", "'none', 'low', and 'high'")
        with patch(CREATE_PATCH, side_effect=[rejection, response]) as create:
            result = self.client.create_completion(kwargs)
        self.assertIs(result, response)
        self.assertNotIn("temperature", create.call_args_list[0].kwargs)
        self.assertNotIn("reasoning_effort", create.call_args.kwargs)
        self.assertEqual(create.call_args.kwargs["temperature"], 0.2)
        self.assertEqual(module.SUPPORTED_REASONING_EFFORTS[UNKNOWN_MODEL], ("none", "low", "high"))

    def test_rejections_are_retried_a_few_times_at_most(self):
        """A model that keeps rejecting what Smarter learns fails after MAX_REQUEST_ATTEMPTS requests."""
        rejections = [bad_request("temperature")] * (module.MAX_REQUEST_ATTEMPTS + 1)
        self.client.model = UNKNOWN_MODEL
        with patch.object(model_quirks, "apply_model_quirks"), patch.object(module, "apply_model_quirks"):
            with patch(CREATE_PATCH, side_effect=rejections) as create:
                with patch.object(OpenAISmarterClient, "learn_from_rejection", return_value=True):
                    with self.assertRaises(openai.BadRequestError):
                        self.client.create_completion(self.kwargs(UNKNOWN_MODEL))
        self.assertEqual(create.call_count, module.MAX_REQUEST_ATTEMPTS)

    def kwargs(self, model: str, reasoning_effort: bool = False) -> SmarterDictType:
        self.client.model = model
        kwargs = {"model": model, "messages": [{"role": "user", "content": "hi"}], "temperature": 0.2}
        if reasoning_effort:
            kwargs["reasoning_effort"] = REASONING_EFFORT_NONE
        return kwargs

    def test_known_model_omits_temperature(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_completion(self.kwargs("gpt-6-luna"))
        create.assert_called_once()
        self.assertNotIn("temperature", create.call_args.kwargs)

    def test_known_model_with_reasoning_effort_none_keeps_temperature(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_completion(self.kwargs("gpt-6-luna", reasoning_effort=True))
        self.assertEqual(create.call_args.kwargs["temperature"], 0.2)

    def test_other_model_keeps_temperature(self):
        with patch(CREATE_PATCH) as create:
            self.client.create_completion(self.kwargs("gpt-4o-mini"))
        self.assertEqual(create.call_args.kwargs["temperature"], 0.2)

    def test_unknown_model_is_retried_and_remembered(self):
        response = MagicMock()
        with patch(CREATE_PATCH, side_effect=[bad_request("temperature"), response]) as create:
            result = self.client.create_completion(self.kwargs(UNKNOWN_MODEL))
        self.assertIs(result, response)
        self.assertEqual(create.call_count, 2)
        self.assertNotIn("temperature", create.call_args.kwargs)
        self.assertIn(UNKNOWN_MODEL, module.DEFAULT_TEMPERATURE_ONLY_MODELS)

        # the next request omits temperature up front
        with patch(CREATE_PATCH) as create:
            self.client.create_completion(self.kwargs(UNKNOWN_MODEL))
        create.assert_called_once()
        self.assertNotIn("temperature", create.call_args.kwargs)

    def test_rejection_with_reasoning_effort_is_retried_but_not_remembered(self):
        response = MagicMock()
        with patch(CREATE_PATCH, side_effect=[bad_request("temperature"), response]) as create:
            result = self.client.create_completion(self.kwargs(UNKNOWN_MODEL, reasoning_effort=True))
        self.assertIs(result, response)
        self.assertNotIn("temperature", create.call_args.kwargs)
        self.assertNotIn(UNKNOWN_MODEL, module.DEFAULT_TEMPERATURE_ONLY_MODELS)

    def test_other_bad_request_is_not_retried(self):
        with patch(CREATE_PATCH, side_effect=bad_request("max_completion_tokens")) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_completion(self.kwargs(UNKNOWN_MODEL))
        create.assert_called_once()
        self.assertNotIn(UNKNOWN_MODEL, module.DEFAULT_TEMPERATURE_ONLY_MODELS)

    def test_rejection_without_temperature_is_not_retried(self):
        kwargs = self.kwargs("gpt-6-luna")
        with patch(CREATE_PATCH, side_effect=bad_request("temperature")) as create:
            with self.assertRaises(openai.BadRequestError):
                self.client.create_completion(kwargs)
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

    llmclient: LLMClient
    prompt: Prompt

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


class TestModelWarnings(SmarterTestBase):
    """
    Test the smarter messages that warn, in Smarter Chat's sandbox mode, that an LLMClient's settings.

    don't suit its model, and say what they should be.
    """

    def setUp(self):
        super().setUp()
        # the handler's other state is not needed to send a request
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        patcher = patch.object(self.client, "append_message")
        self.append_message = patcher.start()
        self.addCleanup(patcher.stop)
        self.prompt = MagicMock()
        self.prompt.llmclient.default_temperature = 0.2
        self.prompt.llmclient.default_reasoning_effort = None
        patcher = patch.object(OpenAISmarterClient, "prompt", new_callable=PropertyMock, return_value=self.prompt)
        patcher.start()
        self.addCleanup(patcher.stop)
        patch_model_set(self, "DEFAULT_TEMPERATURE_ONLY_MODELS", {"gpt-6-luna"})
        patch_model_set(self, "TOOLS_UNSUPPORTED_MODELS", {"gpt-6.1-sol"})
        patch_model_set(self, "TOOLS_REQUIRE_NO_REASONING_MODELS", {"gpt-6-luna"})
        patch_model_set(self, "TOOLS_REJECT_REASONING_EFFORT_MODELS", set())
        efforts = {"gpt-6-luna": ("none", "low", "medium", "high", "xhigh"), "gpt-4o": ()}
        patch_model_set(self, "SUPPORTED_REASONING_EFFORTS", efforts)

    def test_unsupported_reasoning_effort_warns_with_the_closest(self):
        self.prompt.llmclient.default_temperature = None
        self.prompt.llmclient.default_reasoning_effort = "minimal"
        kwargs = self.kwargs("gpt-6-luna")
        kwargs["reasoning_effort"] = "minimal"
        with patch(CREATE_PATCH):
            self.client.create_completion(kwargs)
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("defaultReasoningEffort: low", warnings[0])

    def test_reasoning_effort_on_a_model_that_does_not_reason(self):
        self.prompt.llmclient.default_temperature = None
        self.prompt.llmclient.default_reasoning_effort = "high"
        kwargs = self.kwargs("gpt-4o")
        kwargs["reasoning_effort"] = "high"
        with patch(CREATE_PATCH) as create:
            self.client.create_completion(kwargs)
        self.assertNotIn("reasoning_effort", create.call_args.kwargs)
        self.assertIn("doesn't reason", self.warnings()[0])

    def test_tools_at_none_warn_about_the_llmclients_effort(self):
        self.prompt.llmclient.default_temperature = None
        self.prompt.llmclient.default_reasoning_effort = "high"
        kwargs = self.kwargs("gpt-6-luna")
        kwargs["tools"] = TOOLS
        kwargs["reasoning_effort"] = "high"
        with patch(CREATE_PATCH) as create:
            self.client.create_first_completion(kwargs)
        self.assertEqual(create.call_args.kwargs["reasoning_effort"], "none")
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("defaultModel: gpt-5.2", warnings[0])

    def test_temperature_while_reasoning_warns(self):
        self.prompt.llmclient.default_reasoning_effort = "high"
        kwargs = self.kwargs("gpt-6-luna")
        kwargs["reasoning_effort"] = "high"
        with patch(CREATE_PATCH) as create:
            self.client.create_completion(kwargs)
        self.assertNotIn("temperature", create.call_args.kwargs)
        self.assertIn("defaultReasoningEffort: none", self.warnings()[0])

    def kwargs(self, model: str) -> SmarterDictType:
        self.client.model = model
        return {"model": model, "messages": [{"role": "user", "content": "hi"}], "temperature": 0.2}

    def warnings(self) -> list[str]:
        return [call.kwargs["content"] for call in self.append_message.call_args_list]

    def test_known_model_warns_about_the_llmclients_temperature(self):
        with patch(CREATE_PATCH):
            self.client.create_completion(self.kwargs("gpt-6-luna"))
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("defaultTemperature: 0.2", warnings[0])
        self.assertIn("defaultTemperature: 1.0", warnings[0])
        self.assertIn("defaultReasoningEffort: none", warnings[0])
        role = self.append_message.call_args.kwargs["role"]
        self.assertEqual(role, "smarter")

    def test_rejected_temperature_warns(self):
        with patch(CREATE_PATCH, side_effect=[bad_request("temperature"), MagicMock()]):
            self.client.create_completion(self.kwargs(UNKNOWN_MODEL))
        self.assertEqual(len(self.warnings()), 1)
        self.assertIn(UNKNOWN_MODEL, self.warnings()[0])

    def test_platform_default_temperature_does_not_warn(self):
        """The platform's default temperature isn't the LLMClient's setting, so it's left out silently."""
        self.prompt.llmclient.default_temperature = None
        with patch(CREATE_PATCH):
            self.client.create_completion(self.kwargs("gpt-6-luna"))
        self.append_message.assert_not_called()

    def test_default_temperature_on_a_default_only_model_does_not_warn(self):
        """The model ran at its default, 1.0, which is what the LLMClient asked for (#993)."""
        self.prompt.llmclient.default_temperature = 1.0
        with patch(CREATE_PATCH) as create:
            self.client.create_completion(self.kwargs("gpt-6-luna"))
        self.assertNotIn("temperature", create.call_args.kwargs)
        self.append_message.assert_not_called()

    def test_default_temperature_on_a_model_that_rejects_temperature_warns(self):
        """A search model rejects every temperature, so it didn't use the LLMClient's 1.0 either."""
        patch_model_set(self, "DEFAULT_TEMPERATURE_ONLY_MODELS", {"gpt-5-search-api"})
        patch_model_set(self, "TEMPERATURE_REJECTED_MODELS", {"gpt-5-search-api"})
        self.prompt.llmclient.default_temperature = 1.0
        with patch(CREATE_PATCH):
            self.client.create_completion(self.kwargs("gpt-5-search-api"))
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("defaultTemperature: 1.0", warnings[0])

    def test_a_warning_is_shown_once_per_prompt(self):
        """A prompt's later requests, e.g. after tool calls, don't repeat a warning."""
        with patch(CREATE_PATCH):
            self.client.create_completion(self.kwargs("gpt-6-luna"))
            self.client.create_completion(self.kwargs("gpt-6-luna"))
        self.assertEqual(len(self.warnings()), 1)

        # the handler starts each prompt with no warnings
        self.client.model_warnings = set()
        with patch(CREATE_PATCH):
            self.client.create_completion(self.kwargs("gpt-6-luna"))
        self.assertEqual(len(self.warnings()), 2)

    def test_tools_warning_says_which_model_to_use(self):
        kwargs = self.kwargs("gpt-6.1-sol")
        kwargs["tools"] = TOOLS
        with patch(CREATE_PATCH):
            self.client.create_first_completion(kwargs)
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("get_current_weather", warnings[0])
        self.assertIn("defaultModel: gpt-6-luna", warnings[0])
