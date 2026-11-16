"""Test the Smarter Journal's Django admin."""

from unittest.mock import MagicMock

from django.test import RequestFactory
from pydantic import JsonValue

from smarter.lib.journal.admin import SAMJournalAdmin, prompt_text, response_text
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
