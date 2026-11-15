"""
The prompt app's journal sources: the data of its responses that the journal reads from the database.

An LLMClient's configuration (``/config/``) returns the chat session's whole thread, read from its
newest :class:`~smarter.apps.prompt.models.PromptHistory` row. The configuration's journaled response
names it as the :data:`CHAT_HISTORY_SOURCE` source, so that the thread doesn't pass through the Celery
broker with every request: the journal's task reads it back here. See
:mod:`smarter.lib.journal.sources`.
"""

from pydantic import JsonValue, TypeAdapter

from smarter.lib.journal.sources import (
    JournalSourceGone,
    JournalSourceLookup,
    JournalSourceNotReady,
    SAMJournalSource,
    register_journal_source,
)

from .contract.models import PromptChatApiMessage
from .models import Prompt, PromptHistory

CHAT_HISTORY_SOURCE = "prompt.chat_history"
"""The name of the source of a configuration's ``data.history.chat_history``."""

CHAT_HISTORY_PATH = ("data", "history", "chat_history")
"""Where a configuration's response holds the chat thread."""

PROMPT_HISTORY_ID = "prompt_history_id"
"""The lookup's key of the PromptHistory row's id."""

PROMPT_ID = "prompt_id"
"""The lookup's key of the row's Prompt, the chat session, which tells a row that is not written yet from one that is gone."""

MESSAGES_ADAPTER = TypeAdapter(list[PromptChatApiMessage])
"""Validates and dumps the thread as the configuration does: a list of the contract's messages."""


def chat_history_source(row: PromptHistory) -> SAMJournalSource:
    """
    Return the journal source of a configuration's chat thread.

    :param row: The PromptHistory row that the thread was read from.
    :returns: The source, for ``SmarterJournaledJsonResponse(journal_sources=...)``.
    """
    lookup: JournalSourceLookup = {PROMPT_HISTORY_ID: row.pk, PROMPT_ID: row.prompt_id}  # type: ignore[attr-defined]
    source = SAMJournalSource(name=CHAT_HISTORY_SOURCE, path=CHAT_HISTORY_PATH, lookup=lookup)
    return source


def chat_history_messages(row: PromptHistory) -> JsonValue:
    """
    Return a row's chat thread, as a configuration's response holds it.

    :param row: The PromptHistory row.
    :returns: The thread's messages, validated by the contract and dumped as JSON.
    """
    messages = MESSAGES_ADAPTER.validate_python(row.prompt_history)
    dumped = MESSAGES_ADAPTER.dump_python(messages, mode="json", exclude_unset=True)
    return dumped


def resolve_chat_history(lookup: JournalSourceLookup) -> JsonValue:
    """
    Read a configuration's chat thread from its PromptHistory row, for the journal.

    :param lookup: The source's lookup, from :func:`chat_history_source`.
    :returns: The thread, as the client received it.
    :raises JournalSourceNotReady: If the row isn't written yet, while its chat session exists.
    :raises JournalSourceGone: If the row and its chat session were deleted.
    """
    prompt_history_id = int(lookup[PROMPT_HISTORY_ID])
    row = PromptHistory.objects.filter(pk=prompt_history_id).first()
    if row is not None:
        messages = chat_history_messages(row)
        return messages
    prompt_id = int(lookup[PROMPT_ID])
    if not Prompt.objects.filter(pk=prompt_id).exists():
        raise JournalSourceGone(f"PromptHistory {prompt_history_id} and its Prompt {prompt_id} were deleted.")
    raise JournalSourceNotReady(f"PromptHistory {prompt_history_id} is not written yet.")


def register() -> None:
    """Register the prompt app's journal sources.

    Called by ``PromptConfig.ready()``.
    """
    register_journal_source(CHAT_HISTORY_SOURCE, resolve_chat_history)
