"""Test OpenAIPassthroughClient request normalization."""

from unittest.mock import patch

import httpx
import openai

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
