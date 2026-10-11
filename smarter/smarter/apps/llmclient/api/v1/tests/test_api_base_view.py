"""
Test the guard branches of :class:`smarter.apps.llmclient.api.v1.views.base.LLMClientApiBaseViewSet`.

The view's request-derived properties are replaced, so that each guard is reached on its own.
"""

import asyncio
import json
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch

from django.http import StreamingHttpResponse
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.api.v1.views.base import LLMClientApiBaseViewSet
from smarter.apps.llmclient.exceptions import SmarterLLMClientException
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.contract.models import (
    PromptChatApiErrorResponse,
    PromptChatApiPromptResponse,
)

MODULE = "smarter.apps.llmclient.api.v1.views.base"
HARNESS = "smarter.apps.provider.services.text_completion.providers.smarter_compatible_client"


class TestLLMClientApiBaseViewSet(TestAccountMixin):
    """Test the llmclient api base view's guards against missing or invalid context."""

    def view(self, **properties) -> LLMClientApiBaseViewSet:
        """A view whose named properties return the given values."""
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name, value in properties.items():
            stack.enter_context(
                patch.object(LLMClientApiBaseViewSet, name, new_callable=PropertyMock, return_value=value)
            )
        return LLMClientApiBaseViewSet()

    def post_properties(self, **overrides) -> dict:
        """Properties under which post() passes every guard."""
        properties = {
            "llmclient": MagicMock(),
            "chat_helper": MagicMock(),
            "data": {"messages": []},
            "user": self.admin_user,
            "user_profile": self.user_profile,
            "account": self.account,
            "account_number": self.account.account_number,
            "plugins": [],
            "smarter_request": None,
            "name": "test",
            "session_key": "session",
        }
        properties.update(overrides)
        return properties

    def post(self, **overrides):
        request = RequestFactory().post("/api/v1/llm-clients/1/prompt/")
        request.user = self.admin_user
        with patch(HARNESS):
            return self.view(**self.post_properties(**overrides)).post(request)

    def post_with_harness(self, handler, include_diagnostics: bool = False, **headers):
        """Post() with a prompt handler, and the given request headers."""
        request = RequestFactory().post("/api/v1/llm-clients/1/prompt/", **headers)
        request.user = self.admin_user
        with patch(HARNESS) as harness:
            harness.get_smarter_harness.return_value = handler
            view = self.view(**self.post_properties())
            view.include_diagnostics = include_diagnostics
            return view.post(request)

    @staticmethod
    def lambda_response(body: dict, status: int = HTTPStatus.OK.value) -> dict:
        """A prompt's Lambda style result, as the provider's handler returns it."""
        return {"isBase64Encoded": False, "statusCode": status, "headers": {}, "body": json.dumps(body)}

    @staticmethod
    def stream_events(response: StreamingHttpResponse) -> list[str]:
        """The frames of a streaming response."""

        async def collect():
            frames = []
            async for chunk in response.streaming_content:
                frames.append(chunk.decode() if isinstance(chunk, (bytes, bytearray)) else chunk)
            return frames

        return asyncio.run(collect())

    def test_post_returns_the_prompt_as_json(self):
        handler = MagicMock(return_value={"statusCode": HTTPStatus.OK.value, "body": "{}"})
        response = self.post_with_harness(handler, HTTP_X_SMARTER_CAPABILITIES="chat-contract-v1")
        self.assertNotIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(response.content)["data"]["body"], "{}")

    def test_post_streams_the_prompt_to_a_client_that_accepts_server_sent_events(self):
        handler = MagicMock(return_value={"statusCode": HTTPStatus.UNAUTHORIZED.value, "body": "{}"})
        response = self.post_with_harness(
            handler, HTTP_ACCEPT="text/event-stream, application/json", HTTP_X_SMARTER_CAPABILITIES="chat-contract-v1"
        )
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        frames = self.stream_events(response)
        handler.assert_called_once()
        result = json.loads(frames[-1].split("data: ", 1)[1])
        self.assertEqual(result["status"], HTTPStatus.UNAUTHORIZED.value)
        self.assertEqual(result["response"]["data"]["statusCode"], HTTPStatus.UNAUTHORIZED.value)

    def test_post_streams_a_failed_prompt_as_an_error_result(self):
        handler = MagicMock(side_effect=RuntimeError("the LLM is down"))
        response = self.post_with_harness(handler, HTTP_ACCEPT="text/event-stream")
        result = json.loads(self.stream_events(response)[-1].split("data: ", 1)[1])
        self.assertEqual(result["status"], HTTPStatus.INTERNAL_SERVER_ERROR.value)
        # the exception's text and stack trace are logged, never returned to a browser.
        error = result["response"]["error"]
        self.assertEqual(error["description"], "An error occurred while processing your prompt.")
        self.assertNotIn("stacktrace", error)
        self.assertNotIn("the LLM is down", json.dumps(result["response"]))

    def test_post_without_an_llmclient_is_not_found(self):
        self.assertEqual(self.post(llmclient=None).status_code, HTTPStatus.NOT_FOUND)

    def test_post_without_a_chat_helper_is_not_found(self):
        self.assertEqual(self.post(chat_helper=None).status_code, HTTPStatus.NOT_FOUND)

    def test_post_guards_raise(self):
        for overrides in (
            {"chat_helper": MagicMock(prompt=None)},
            {"data": None},
            {"data": "not a dict"},
            {"user": MagicMock()},
            {"user_profile": MagicMock()},
        ):
            with self.subTest(overrides=list(overrides)):
                with self.assertRaises(SmarterLLMClientException):
                    self.post(**overrides)

    def test_chat_helper_requires_a_session_or_llmclient(self):
        view = self.view(session_key=None, llmclient=None, smarter_request=None, name=None, user_profile=None)
        with self.assertRaises(SmarterLLMClientException):
            _ = view.chat_helper

    def test_llmclient_helper_requires_identifying_properties(self):
        view = self.view(url=None, llmclient_id=None, user_profile=None)
        self.assertIsNone(view.llmclient_helper)

    def test_llmclient_helper_for_an_unknown_llmclient(self):
        view = self.view(
            url=None, llmclient_id=999999999, name=None, smarter_request=None, session_key=None, user_profile=None
        )
        view._account = None
        view._user = None
        with patch(f"{MODULE}.LLMClientHelper", side_effect=LLMClient.DoesNotExist("nope")):
            with self.assertRaises(LLMClient.DoesNotExist):
                _ = view.llmclient_helper

    def test_is_web_platform(self):
        request = MagicMock()
        request.get_host.return_value = "not-the-platform.example.com"
        self.assertFalse(self.view(smarter_request=request).is_web_platform)
        with patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment_platform_domain = "not-the-platform.example.com"
            self.assertTrue(self.view(smarter_request=request).is_web_platform)

    COMPLETION = {
        "id": "chatcmpl-1",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi"}}],
        "smarter": {
            "first_iteration": {"request": {"messages": [{"role": "system", "content": "secret"}]}},
            "second_iteration": {},
            "plugins": ["p"],
            "messages": [{"role": "assistant", "content": "hi"}],
        },
    }

    def test_post_strips_the_llm_requests_from_a_browser_response(self):
        handler = MagicMock(return_value=self.lambda_response(self.COMPLETION))
        body = json.loads(
            json.loads(self.post_with_harness(handler, HTTP_X_SMARTER_CAPABILITIES="chat-contract-v1").content)["data"][
                "body"
            ]
        )
        self.assertNotIn("first_iteration", body["smarter"])
        self.assertNotIn("second_iteration", body["smarter"])
        self.assertEqual(body["smarter"]["messages"], [{"role": "assistant", "content": "hi"}])

    def test_post_keeps_the_llm_requests_for_the_cli(self):
        handler = MagicMock(return_value=self.lambda_response(self.COMPLETION))
        response = self.post_with_harness(
            handler, include_diagnostics=True, HTTP_X_SMARTER_CAPABILITIES="chat-contract-v1"
        )
        body = json.loads(json.loads(response.content)["data"]["body"])
        self.assertIn("first_iteration", body["smarter"])

    def test_post_returns_version_2_of_the_contract_to_a_client_that_asks_for_it(self):
        handler = MagicMock(return_value=self.lambda_response(self.COMPLETION))
        response = self.post_with_harness(handler, HTTP_X_SMARTER_CAPABILITIES="chat-contract-v2")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        payload = PromptChatApiPromptResponse.model_validate(json.loads(response.content))
        self.assertEqual(payload.data.contract, 2)
        self.assertEqual(payload.data.messages[0].content, "hi")
        self.assertEqual(payload.data.plugins, ["p"])
        self.assertIsNone(payload.error)
        self.assertNotIn("secret", response.content.decode())

    def test_post_returns_version_2_by_default(self):
        handler = MagicMock(return_value=self.lambda_response(self.COMPLETION))
        payload = PromptChatApiPromptResponse.model_validate(json.loads(self.post_with_harness(handler).content))
        self.assertEqual(payload.data.contract, 2)

    def test_post_returns_a_failed_prompt_in_version_2_with_the_error_envelope(self):
        failure = {
            "error": {"status": 429, "message": "Rate limit reached."},
            "response": {
                "smarter": {"messages": [{"role": "smarter_error", "content": "429 error: Rate limit reached."}]}
            },
        }
        handler = MagicMock(return_value=self.lambda_response(failure, status=429))
        response = self.post_with_harness(handler, HTTP_X_SMARTER_CAPABILITIES="chat-contract-v2")
        self.assertEqual(response.status_code, 429)
        payload = PromptChatApiPromptResponse.model_validate(json.loads(response.content))
        self.assertEqual(payload.error.description, "Rate limit reached.")
        self.assertEqual(payload.error.errorClass, "PromptChatApiErrorLLMProvider")
        self.assertEqual(payload.data.messages[0].role, "smarter_error")

    def test_post_errors_share_one_envelope(self):
        response = self.post(llmclient=None)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        error = PromptChatApiErrorResponse.model_validate(json.loads(response.content)).error
        self.assertEqual(error.errorClass, "PromptChatApiErrorNotFound")
        self.assertNotIn("stacktrace", json.loads(response.content)["error"])
