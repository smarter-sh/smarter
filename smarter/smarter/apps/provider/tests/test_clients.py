# pylint: disable=unused-argument
"""Test OpenAIPassthroughClient request normalization."""

from unittest.mock import MagicMock, patch

import httpx
import openai
from openai.types.chat.chat_completion import ChatCompletion

from smarter.apps.provider.clients import OpenAIPassthroughClient
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestOpenAIPassthroughClientNormalize(SmarterTestBase):
    """Test OpenAIPassthroughClient.normalize_request_data()."""

    def test_openai_max_tokens_renamed(self):
        data = {"model": "gpt-5", "max_tokens": 1024}
        result = OpenAIPassthroughClient.normalize_request_data("openai", data)
        self.assertEqual(result, {"model": "gpt-5", "max_completion_tokens": 1024})

    def test_openai_explicit_max_completion_tokens_wins(self):
        data = {"max_tokens": 1024, "max_completion_tokens": 256}
        result = OpenAIPassthroughClient.normalize_request_data("openai", data)
        self.assertEqual(result, {"max_completion_tokens": 256})

    def test_openai_without_max_tokens_unchanged(self):
        data = {"model": "gpt-5", "max_completion_tokens": 512}
        result = OpenAIPassthroughClient.normalize_request_data("openai", data)
        self.assertEqual(result, {"model": "gpt-5", "max_completion_tokens": 512})

    def test_other_providers_unchanged(self):
        for provider in ("googleai", "metaai"):
            with self.subTest(provider=provider):
                data = {"max_tokens": 1024}
                result = OpenAIPassthroughClient.normalize_request_data(provider, data)
                self.assertEqual(result, {"max_tokens": 1024})

    def test_non_dict_unchanged(self):
        self.assertEqual(OpenAIPassthroughClient.normalize_request_data("openai", []), [])


def bad_request(param: str) -> openai.BadRequestError:
    """An OpenAI 400 error for the given request parameter."""
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))
    return openai.BadRequestError("bad request", response=response, body={"param": param})


class TestOpenAIPassthroughClientReasoningEffort(SmarterTestBase):
    """Test the reasoning_effort retry of OpenAIPassthroughClient.create_chat_completion()."""

    def setUp(self):
        super().setUp()
        self.client = OpenAIPassthroughClient(provider="openai", base_url="", api_key="")
        self.data = {"model": "gpt-6-luna", "messages": [], "tools": [{"type": "function"}]}

    def test_requires_reasoning_effort_none(self):
        e = bad_request("reasoning_effort")
        self.assertTrue(OpenAIPassthroughClient.requires_reasoning_effort_none("openai", self.data, e))
        self.assertFalse(OpenAIPassthroughClient.requires_reasoning_effort_none("googleai", self.data, e))
        self.assertFalse(
            OpenAIPassthroughClient.requires_reasoning_effort_none("openai", {**self.data, "tools": []}, e)
        )
        self.assertFalse(
            OpenAIPassthroughClient.requires_reasoning_effort_none(
                "openai", {**self.data, "reasoning_effort": "low"}, e
            )
        )
        self.assertFalse(
            OpenAIPassthroughClient.requires_reasoning_effort_none("openai", self.data, bad_request("temperature"))
        )

    @patch("smarter.apps.provider.clients.openai.chat.completions.create")
    def test_retries_with_reasoning_effort_none(self, mock_create):
        mock_create.side_effect = [bad_request("reasoning_effort"), "completion"]
        with self.assertLogs("smarter.apps.provider.clients", level="WARNING") as logs:
            result = self.client.create_chat_completion(self.data, "prefix")
        self.assertEqual(result, "completion")
        self.assertEqual(mock_create.call_count, 2)
        self.assertEqual(mock_create.call_args.kwargs["reasoning_effort"], "none")
        self.assertIn("reasoning_effort='none'", logs.output[0])

    @patch("smarter.apps.provider.clients.openai.chat.completions.create")
    def test_other_errors_not_retried(self, mock_create):
        mock_create.side_effect = bad_request("temperature")
        with self.assertRaises(openai.BadRequestError):
            self.client.create_chat_completion(self.data, "prefix")
        self.assertEqual(mock_create.call_count, 1)


class TestOpenAIPassthroughClientHandlerLogging(SmarterTestBase):
    """Test that OpenAIPassthroughClient.handler() never logs its API key."""

    @patch("smarter.apps.provider.clients.SmarterHttpResponseNotFound")
    @patch("smarter.apps.provider.clients.charge_authorization")
    @patch("smarter.apps.provider.clients.Provider")
    def test_api_key_is_masked(self, mock_provider, mock_charge_authorization, mock_not_found):
        mock_provider.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_provider.objects.filter.return_value.with_read_permission_for.return_value.first.return_value = None
        client = OpenAIPassthroughClient(provider="openai", base_url="", api_key="sk-test-0123456789abcdef")
        request = MagicMock()
        request.user.is_authenticated = True
        with patch("smarter.apps.provider.clients.logger") as logger:
            client.handler(request=request, user_profile=MagicMock(), data={})
        logged = str(logger.mock_calls)
        self.assertIn("api_key", logged)
        self.assertNotIn("sk-test-0123456789abcdef", logged)


class TestOpenAIPassthroughClientHandlerChatContent(SmarterTestBase):
    """Test that OpenAIPassthroughClient.handler() never logs chat content."""

    marker = "private-chat-content"

    def build_client(self, mock_provider) -> OpenAIPassthroughClient:
        """A client whose Provider lookup finds a provider without an api key."""
        provider = MagicMock()
        provider.api_key = None
        provider.base_url = "https://example.com/v1/"
        mock_provider.objects.filter.return_value.with_read_permission_for.return_value.first.return_value = provider
        client = OpenAIPassthroughClient(provider="openai", base_url="", api_key="")
        return client

    def build_request(self, body: str) -> MagicMock:
        """An authenticated request with the given body."""
        request = MagicMock()
        request.user.is_authenticated = True
        request.body = body.encode("utf-8")
        return request

    def assert_marker_not_logged(self, mock_logger: MagicMock):
        """The marker is in no call to the logger."""
        for logged_call in mock_logger.mock_calls:
            self.assertNotIn(self.marker, str(logged_call))

    @patch("smarter.apps.provider.clients.SmarterHttpResponseBadRequest")
    @patch("smarter.apps.provider.clients.charge_authorization")
    @patch("smarter.apps.provider.clients.Provider")
    def test_invalid_json_body_is_logged_without_the_body(self, mock_provider, *mocks):
        client = self.build_client(mock_provider)
        body = '{"messages": [{"role": "user", "content": "' + self.marker + '"}]'
        request = self.build_request(body)
        with patch("smarter.apps.provider.clients.logger") as mock_logger:
            client.handler(request=request, user_profile=MagicMock(), data={})
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_called_once()
        self.assert_marker_not_logged(mock_logger)

    @patch("smarter.apps.provider.clients.SmarterJournaledJsonErrorResponse")
    @patch("smarter.apps.provider.clients.chat_response_failure")
    @patch("smarter.apps.provider.clients.chat_request")
    @patch("smarter.apps.provider.clients.prompt_started")
    @patch("smarter.apps.provider.clients.charge_authorization")
    @patch("smarter.apps.provider.clients.Provider")
    def test_failed_call_does_not_log_the_request(self, mock_provider, *mocks):
        client = self.build_client(mock_provider)
        body = '{"model": "gpt-40-mini", "messages": [{"role": "user", "content": "' + self.marker + '"}]}'
        request = self.build_request(body)
        with patch.object(client, "create_chat_completion", side_effect=RuntimeError("model_not_found")):
            with patch("smarter.apps.provider.clients.logger") as mock_logger:
                client.handler(request=request, user_profile=MagicMock(), data={})
        mock_logger.error.assert_called_once()
        self.assert_marker_not_logged(mock_logger)

    @patch("smarter.apps.provider.clients.SmarterJournaledJsonResponse")
    @patch("smarter.apps.provider.clients.prompt_finished")
    @patch("smarter.apps.provider.clients.chat_response")
    @patch("smarter.apps.provider.clients.chat_request")
    @patch("smarter.apps.provider.clients.prompt_started")
    @patch("smarter.apps.provider.clients.charge_authorization")
    @patch("smarter.apps.provider.clients.Provider")
    def test_successful_call_does_not_log_the_request_or_reply(self, mock_provider, *mocks):
        client = self.build_client(mock_provider)
        body = '{"model": "gpt-5", "messages": [{"role": "user", "content": "' + self.marker + '"}]}'
        request = self.build_request(body)
        completion = ChatCompletion.model_validate(
            {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-5",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": self.marker},
                    }
                ],
            }
        )
        with patch.object(client, "create_chat_completion", return_value=completion):
            with patch("smarter.apps.provider.clients.logger") as mock_logger:
                client.handler(request=request, user_profile=MagicMock(), data={})
        self.assertIn("chatcmpl-test", str(mock_logger.mock_calls))
        self.assert_marker_not_logged(mock_logger)
