"""Test the prompt app's journal sources: :mod:`smarter.apps.prompt.journal`."""

import json
import secrets
from http import HTTPStatus
from unittest.mock import patch

from celery.exceptions import Retry
from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.api.v1.urls import LLMClientApiV1ReverseViews
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.contract.const import CHAT_CONTRACT_V2_CAPABILITY
from smarter.apps.prompt.journal import (
    CHAT_HISTORY_PATH,
    CHAT_HISTORY_SOURCE,
    PROMPT_HISTORY_ID,
    PROMPT_ID,
    chat_history_messages,
    chat_history_source,
    resolve_chat_history,
)
from smarter.apps.prompt.models import Prompt, PromptHistory
from smarter.lib.django.shortcuts import reverse
from smarter.lib.journal.models import SAMJournal
from smarter.lib.journal.sources import (
    JournalSourceGone,
    JournalSourceLookup,
    JournalSourceNotReady,
    get_at_path,
)
from smarter.lib.journal.tasks import (
    SAMJournalEntryRecord,
    create_journal_entry,
    queue_journal_entry,
)

MESSAGES = [
    {"role": "system", "content": "journal thread marker. " * 100, "smarter_is_new": False},
    {"role": "user", "content": "hello", "smarter_is_new": False},
    {"role": "assistant", "content": "hi there", "annotations": [], "smarter_is_new": True},
    {"role": "smarter_error", "content": "a failure", "smarter_is_new": True},
]
"""A saved conversation, with Smarter's own messages and fields."""


class TestPromptJournal(TestAccountMixin):
    """Test that a configuration's chat thread is journaled from its PromptHistory row, not through the broker."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_prompt_journal_{self.hash_suffix}",
            user_profile=self.user_profile,
            default_model="gpt-test",
            default_system_role="You are a test.",
            app_welcome_message="Welcome!",
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.addCleanup(Prompt.objects.filter(llmclient=self.llmclient).delete)
        self.prompt = Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=self.user_profile,
            llmclient=self.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.example.com",
        )
        self.row = PromptHistory.objects.create(prompt=self.prompt, request={}, response={}, messages=MESSAGES)
        self.client = Client()
        self.client.force_login(self.admin_user)
        switch = patch("smarter.lib.django.waffle.switch_is_active", return_value=True)
        switch.start()
        self.addCleanup(switch.stop)

    def config(self, **headers):
        """POST the configuration api, and return its response, the queued entry, and its JSON payload."""
        name = LLMClientApiV1ReverseViews.chat_config_view_by_hashed_id
        path = reverse(f"{LLMClientApiV1ReverseViews.namespace}:{name}", kwargs={"hashed_id": self.llmclient.hashed_id})
        queued: list[dict] = []
        with (
            patch("smarter.lib.journal.http.queue_journal_entry", side_effect=queue_journal_entry),
            patch("smarter.lib.journal.tasks.create_journal_entry.delay", side_effect=queued.append),
        ):
            response = self.client.post(
                f"{path}?session_key={self.prompt.session_key}", data="{}", content_type="application/json", **headers
            )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual(len(queued), 1)
        return response, queued[0]

    def test_config_is_journaled_from_the_row(self):
        """Test that the thread isn't queued, and that the task journals exactly what the client received."""
        for contract, headers in (
            (2, {"HTTP_X_SMARTER_CAPABILITIES": CHAT_CONTRACT_V2_CAPABILITY}),
            (1, {"HTTP_X_SMARTER_CLIENT": "@smarter.sh/ui-chat"}),
        ):
            with self.subTest(contract=contract):
                response, payload = self.config(**headers)
                sent = json.loads(response.content)
                sent_thread = get_at_path(sent, CHAT_HISTORY_PATH)
                self.assertTrue(sent_thread)
                # the queued entry names the thread, and doesn't carry it.
                self.assertIsNone(get_at_path(payload["response"], CHAT_HISTORY_PATH))
                self.assertNotIn("journal thread marker.", json.dumps(payload))
                self.assertEqual(len(payload["sources"]), 1)
                reference = payload["sources"][0]
                self.assertEqual(reference["name"], CHAT_HISTORY_SOURCE)
                self.assertEqual(reference["lookup"][PROMPT_HISTORY_ID], self.row.pk)
                # the worker reads it back, and journals what the client received.
                create_journal_entry(payload)
                entry = SAMJournal.objects.get(key=payload["key"])
                self.addCleanup(entry.delete)
                self.assertEqual(get_at_path(entry.response, CHAT_HISTORY_PATH), sent_thread)

    def test_resolve_chat_history(self):
        """Test that the resolver waits for a row that is not written yet, and gives up on one that is gone."""
        lookup: JournalSourceLookup = {PROMPT_HISTORY_ID: self.row.pk, PROMPT_ID: self.prompt.pk}
        self.assertTrue(resolve_chat_history(lookup))
        with self.assertRaises(JournalSourceNotReady):
            resolve_chat_history({PROMPT_HISTORY_ID: self.row.pk + 1000000, PROMPT_ID: self.prompt.pk})
        with self.assertRaises(JournalSourceGone):
            resolve_chat_history({PROMPT_HISTORY_ID: self.row.pk + 1000000, PROMPT_ID: self.prompt.pk + 1000000})

    def test_row_written_after_the_response(self):
        """Test that an entry whose row is written later, e.g. by a Celery task, is journaled once it exists."""
        record = SAMJournalEntryRecord(
            key=secrets.token_hex(32),
            created_at=self.row.created_at,
            user_id=None,
            thing="ChatConfig",
            command="chat_config",
            status_code=HTTPStatus.OK,
            request={},
            response={"data": {"history": {"chat_history": "placeholder"}}},
        )
        self.addCleanup(SAMJournal.objects.filter(key=record.key).delete)
        later = PromptHistory(prompt=self.prompt, request={}, response={}, messages=MESSAGES)
        # the id that the row will have, before it exists.
        later.pk = PromptHistory.objects.order_by("-pk").values_list("pk", flat=True)[0] + 1000
        queued: list[dict] = []
        response_with_thread = {"data": {"history": {"chat_history": chat_history_messages(later)}}}
        record = record.model_copy(update={"response": response_with_thread})
        with patch("smarter.lib.journal.tasks.create_journal_entry.delay", side_effect=queued.append):
            queue_journal_entry(record, [chat_history_source(later)])
        payload = queued[0]
        with patch.object(create_journal_entry, "retry", side_effect=Retry("retried")) as retry:
            with self.assertRaises(Retry):
                create_journal_entry(payload)
        self.assertIsNone(retry.call_args.kwargs["max_retries"])
        self.assertFalse(SAMJournal.objects.filter(key=record.key).exists())
        later.save(force_insert=True)
        self.addCleanup(PromptHistory.objects.filter(pk=later.pk).delete)
        create_journal_entry(payload)
        entry = SAMJournal.objects.get(key=record.key)
        self.assertEqual(entry.response, response_with_thread)
