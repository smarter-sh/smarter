"""Test the Smarter Journal's Django admin."""

import json
from unittest.mock import MagicMock

from django.test import RequestFactory
from openai.types.chat import ChatCompletion
from pydantic import JsonValue

from smarter.apps.prompt.contract.builders import prompt_result_v2
from smarter.lib.journal.admin import SAMJournalAdmin, prompt_text, response_text
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.journal.models import DOCUMENT_FIELDS, SAMJournal
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSAMJournalAdmin(SmarterTestBase):
    """Test the prompt and response that the admin shows for a journal entry."""

    request: JsonValue = {
        "path": "/api/v1/prompts/passthrough/openai/",
        "body": {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What's the weather?"},
                {"role": "assistant", "content": "Where?"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "In San Francisco?"},
                        {"type": "image_url", "image_url": {"url": "https://example.com/sf.png"}},
                    ],
                },
            ],
        },
    }
    response: JsonValue = {
        "id": "chatcmpl-example",
        "object": "chat.completion",
        "created": 1794809744,
        "model": "gpt-4o-mini-2024-07-18",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "It's 63F right now."},
            }
        ],
        "api": "smarter.sh/v1",
        "metadata": {"command": "prompt", "thing": "Prompt"},
    }

    def test_prompt_is_the_last_user_message(self):
        self.assertEqual(prompt_text(self.request), "In San Francisco?")

    def test_prompt_as_a_string(self):
        request: JsonValue = {"body": {"messages": [{"role": "user", "content": "What's the weather?"}]}}
        self.assertEqual(prompt_text(request), "What's the weather?")

    def test_response_is_the_first_choice(self):
        self.assertEqual(response_text(self.response), "It's 63F right now.")

    def lambda_result(self, body: JsonValue) -> dict[str, JsonValue]:
        """A prompt handler's Lambda style result, as an LLMClient's handler returns it."""
        assert isinstance(self.response, dict)
        completion = {key: value for key, value in self.response.items() if key not in ("api", "metadata")}
        completion["smarter"] = {"messages": [{"role": "user", "content": "What's the weather?"}], "tools": []}
        return {"statusCode": 200, "body": body if body is not None else completion}

    def test_response_of_an_llmclient_prompt(self):
        """
        Test the reply of a prompt to an LLMClient, chat contract version 2, which the web console sends.

        The response document is built as the LLMClient's prompt view builds it, with prompt_result_v2(),
        not written by hand.
        """
        data, _, _ = prompt_result_v2(self.lambda_result(None))
        response: JsonValue = {
            SmarterJournalApiResponseKeys.DATA: data,
            "api": "smarter.sh/v1",
            "metadata": {"command": "prompt", "thing": "LLMClient"},
        }
        self.assertEqual(response_text(response), "It's 63F right now.")

    def test_response_of_an_llmclient_prompt_v1(self):
        """Test the reply of a prompt to an LLMClient, chat contract version 1, whose body may be JSON text."""
        completion = self.lambda_result(None)["body"]
        bodies: tuple[JsonValue, ...] = (
            completion,
            json.dumps(completion),
            {"error": {"status": 500}, "response": completion},
        )
        for body in bodies:
            response: JsonValue = {SmarterJournalApiResponseKeys.DATA: {"statusCode": 200, "body": body}}
            self.assertEqual(response_text(response), "It's 63F right now.", body)
        response = {SmarterJournalApiResponseKeys.DATA: {"statusCode": 200, "body": "not json"}}
        self.assertEqual(response_text(response), "")

    def test_response_of_a_passthrough_prompt(self):
        """Test the reply of a passthrough prompt, which journals ChatCompletion.model_dump() itself."""
        completion = ChatCompletion.model_validate(self.response)
        self.assertEqual(response_text(completion.model_dump()), "It's 63F right now.")

    def test_response_without_choices(self):
        response = dict(self.response) if isinstance(self.response, dict) else {}
        response["choices"] = []
        self.assertEqual(response_text(response), "")

    def test_not_a_prompt(self):
        """Entries that aren't chat completions, and those journaled before bodies were, show nothing."""
        requests: tuple[JsonValue, ...] = (
            None,
            {},
            {"body": None},
            {"body": {"messages": "x"}},
            {"body": {"messages": [{"role": "system", "content": "x"}]}},
            {"body": {"messages": [{"role": "user", "content": [{"type": "unknown"}]}]}},
        )
        for request in requests:
            self.assertEqual(prompt_text(request), "", request)
        responses: tuple[JsonValue, ...] = (None, {}, {"choices": ["x"]}, {"data": {"body": "x"}})
        for response in responses:
            self.assertEqual(response_text(response), "", response)

    def test_admin_fields(self):
        model_admin = SAMJournalAdmin(SAMJournal, MagicMock())
        entry = MagicMock(spec=SAMJournal)
        entry.request = self.request
        entry.response = self.response
        self.assertEqual(model_admin.prompt(entry), "In San Francisco?")
        self.assertEqual(model_admin.reply(entry), "It's 63F right now.")

    def test_list_defers_the_documents(self):
        """Test that the admin's queryset doesn't read the entries' compressed documents."""
        model_admin = SAMJournalAdmin(SAMJournal, MagicMock())
        request = RequestFactory().get("/admin/journal/samjournal/")
        queryset = model_admin.get_queryset(request)
        deferred_fields, is_deferred = queryset.query.deferred_loading
        self.assertTrue(is_deferred)
        self.assertEqual(set(deferred_fields), set(DOCUMENT_FIELDS))

    def test_list_columns_are_fields(self):
        """Test that the list's thing and command are the model's choice fields, which the admin sorts by."""
        self.assertIn("thing", SAMJournalAdmin.list_display)
        self.assertIn("command", SAMJournalAdmin.list_display)
