"""Test :mod:`smarter.apps.llmclient.prompting`, which prompts an LLMClient from the platform's own code."""

from http import HTTPStatus
from unittest import mock

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient import prompting
from smarter.apps.llmclient.prompting import (
    SmarterLLMClientPromptError,
    assistant_text,
    prompt_llmclient,
    single_use_api_key,
)
from smarter.apps.prompt.contract.models import (
    PromptChatApiMessage,
    PromptChatApiPromptResult,
)
from smarter.common.const import SmarterEnvironments
from smarter.lib.drf.models import SmarterAuthToken

LLMCLIENT = mock.Mock(id=7)
LLMCLIENT.name = "test_prompting_llmclient"


class TestPrompting(TestAccountMixin):
    """The chat api is patched, so no LLM is called."""

    def post(self, *responses):
        """Patch the chat api's client with responses, in order."""
        api_client = mock.patch.object(prompting, "APIClient")
        patched = api_client.start()
        self.addCleanup(api_client.stop)
        patched.return_value.post.side_effect = list(responses)
        return patched

    @staticmethod
    def response(body, status=HTTPStatus.OK):
        """A chat api response."""
        response = mock.Mock(status_code=status, content=b"the response")
        response.json.return_value = body
        return response

    def test_single_use_api_key_is_deleted(self):
        with single_use_api_key(self.user_profile, "test_prompting") as key:
            self.assertTrue(key)
            self.assertTrue(SmarterAuthToken.objects.filter(name="test_prompting").exists())
        self.assertFalse(SmarterAuthToken.objects.filter(name="test_prompting").exists())

    def test_single_use_api_key_is_deleted_on_error(self):
        with self.assertRaises(RuntimeError):
            with single_use_api_key(self.user_profile, "test_prompting_error"):
                raise RuntimeError("boom")
        self.assertFalse(SmarterAuthToken.objects.filter(name="test_prompting_error").exists())

    def test_prompt_llmclient(self):
        config = self.response({"data": {"session_key": "a-session"}})
        answer = {"role": "assistant", "content": "Hello."}
        prompt = self.response({"api": "smarter.sh/v1", "data": {"status": 200, "messages": [answer]}})
        api_client = self.post(config, prompt)
        result = prompt_llmclient(LLMCLIENT, "a-key", "Hi")
        self.assertEqual(assistant_text(result), "Hello.")
        calls = api_client.return_value.post.call_args_list
        self.assertEqual(
            [call.args[0] for call in calls], ["/api/v1/llm-clients/7/config/", "/api/v1/llm-clients/7/prompt/"]
        )
        self.assertEqual(calls[1].kwargs["data"]["session_key"], "a-session")
        self.assertEqual(calls[1].kwargs["headers"]["Authorization"], "Token a-key")
        self.assertNotIn("Host", calls[1].kwargs["headers"])

    def test_prompt_llmclient_in_aws(self):
        config = self.response({"data": {"session_key": "a-session"}})
        prompt = self.response({"api": "smarter.sh/v1", "data": {"status": 200, "messages": []}})
        api_client = self.post(config, prompt)
        environment = SmarterEnvironments.aws_environments[0]
        settings = mock.Mock(environment=environment, environment_platform_domain="platform.example.com")
        with mock.patch.object(prompting, "smarter_settings", settings):
            prompt_llmclient(LLMCLIENT, "a-key", "Hi")
        headers = api_client.return_value.post.call_args_list[0].kwargs["headers"]
        self.assertEqual(headers["Host"], "platform.example.com")

    def test_prompt_llmclient_failures(self):
        self.post(self.response({}, status=HTTPStatus.UNAUTHORIZED))
        with self.assertRaisesRegex(SmarterLLMClientPromptError, "failed with status 401"):
            prompt_llmclient(LLMCLIENT, "a-key", "Hi")
        config = self.response({"data": {"session_key": "a-session"}})
        invalid = self.response({"data": {"messages": [{"content": "no role"}]}})
        self.post(config, invalid)
        with self.assertRaisesRegex(SmarterLLMClientPromptError, "invalid prompt response"):
            prompt_llmclient(LLMCLIENT, "a-key", "Hi")

    def test_assistant_text(self):
        messages = [
            PromptChatApiMessage(role="assistant", content="First."),
            PromptChatApiMessage(role="tool", content="data"),
            PromptChatApiMessage(role="assistant", content="  "),
            PromptChatApiMessage(role="assistant", content=[{"type": "text", "text": "parts"}]),
            PromptChatApiMessage(role="assistant", content="Last."),
        ]
        self.assertEqual(assistant_text(PromptChatApiPromptResult(status=200, messages=messages)), "Last.")
        self.assertIsNone(assistant_text(PromptChatApiPromptResult(status=200, messages=[])))
