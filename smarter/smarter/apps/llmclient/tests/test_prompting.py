"""Test :mod:`smarter.apps.llmclient.prompting`, which prompts an LLMClient from the platform's own code."""

from http import HTTPStatus
from unittest import mock

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient import prompting
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.prompting import (
    PLATFORM_IP_ADDRESS,
    SmarterLLMClientPromptError,
    assistant_text,
    extract_json_object,
    new_session,
    prompt_in_process,
    prompt_llmclient,
    send_message,
    single_use_api_key,
)
from smarter.apps.prompt.contract.models import (
    PromptChatApiMessage,
    PromptChatApiPromptResult,
)
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.services.text_completion.providers import (
    smarter_compatible_client,
)
from smarter.common.const import SmarterEnvironments
from smarter.lib import json
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

    def test_extract_json_object(self):
        """An LLM's JSON is found in prose or a code block; anything else is no object."""
        self.assertEqual(extract_json_object('Sure: ```json\n{"harness": "a"}\n```'), {"harness": "a"})
        for text in (None, "", "no json here", "{not json}", "[1, 2]", "} backwards {"):
            with self.subTest(text=text):
                self.assertIsNone(extract_json_object(text))


def lambda_response(text: str, status: int = HTTPStatus.OK.value) -> dict:
    """A prompt's result, as the provider's handler returns it, whose assistant answered ``text``."""
    body = {
        "id": "chatcmpl-1",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
        "smarter": {"messages": [{"role": "assistant", "content": text}]},
    }
    response = {"isBase64Encoded": False, "statusCode": status, "headers": {}, "body": json.dumps(body)}
    return response


class TestPromptingInProcess(TestAccountMixin):
    """The provider's handler is patched, so no LLM is called."""

    llmclient: LLMClient

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name=f"test_prompting_{cls.hash_suffix}", user_profile=cls.user_profile, deployed=False
        )

    @classmethod
    def tearDownClass(cls):
        Prompt.objects.filter(llmclient=cls.llmclient).delete()
        LLMClient.objects.filter(pk=cls.llmclient.pk).delete()
        super().tearDownClass()

    def handler(self, **kwargs) -> mock.Mock:
        """Patch the provider's handler, until the end of the test."""
        handler = mock.Mock(**kwargs)
        patcher = mock.patch.object(smarter_compatible_client, "get_smarter_harness", return_value=handler)
        patcher.start()
        self.addCleanup(patcher.stop)
        return handler

    def test_new_session(self):
        """A session belongs to the LLMClient's owner, and says where it came from."""
        session = new_session(self.llmclient, "https://platform.example.com/api/v1/x/", "smarter-test")
        self.assertEqual(session.user_profile, self.user_profile)
        self.assertEqual(session.llmclient, self.llmclient)
        self.assertEqual(session.ip_address, PLATFORM_IP_ADDRESS)
        self.assertEqual(session.user_agent, "smarter-test")
        self.assertEqual(len(session.session_key), 64)

    def test_send_message(self):
        """The message reaches the handler, as the owner, in the session, with the acting user."""
        handler = self.handler(return_value=lambda_response("Hello."))
        session = new_session(self.llmclient, "https://platform.example.com/api/v1/x/", "smarter-test")
        with mock.patch.object(prompting, "acting_user", wraps=prompting.acting_user) as acting:
            result = send_message(session, "Hi", acting=self.non_admin_user)
        self.assertEqual(assistant_text(result), "Hello.")
        user_profile, prompt, data = handler.call_args.args
        self.assertEqual(user_profile, self.user_profile)
        self.assertEqual(prompt, session)
        self.assertEqual(data["session_key"], session.session_key)
        self.assertEqual(data["messages"], [{"role": "user", "content": "Hi"}])
        acting.assert_called_once_with(self.non_admin_user)

    def test_send_message_failures(self):
        """A provider's error, or any exception, is a prompt error, which quotes nothing of an exception."""
        session = new_session(self.llmclient, "https://platform.example.com/api/v1/x/", "smarter-test")
        self.handler(return_value=lambda_response("", status=HTTPStatus.INTERNAL_SERVER_ERROR.value))
        with self.assertRaisesRegex(SmarterLLMClientPromptError, "500"):
            send_message(session, "Hi")
        self.handler(side_effect=RuntimeError("provider secret"))
        with mock.patch.object(prompting, "logger"):
            with self.assertRaises(SmarterLLMClientPromptError) as raised:
                send_message(session, "Hi")
        self.assertNotIn("provider secret", str(raised.exception))
        self.assertIn("RuntimeError", str(raised.exception))

    def test_prompt_in_process(self):
        """One message, in a new session."""
        handler = self.handler(return_value=lambda_response("Hello."))
        before = Prompt.objects.filter(llmclient=self.llmclient).count()
        result = prompt_in_process(self.llmclient, "Hi", "https://platform.example.com/api/v1/x/", "smarter-test")
        self.assertEqual(assistant_text(result), "Hello.")
        self.assertEqual(Prompt.objects.filter(llmclient=self.llmclient).count(), before + 1)
        handler.assert_called_once()
