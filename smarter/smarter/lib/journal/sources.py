"""
Journal sources: parts of a journaled response that the worker reads from the database.

Some responses send data that Smarter has already saved. The largest is an LLMClient's configuration
(``/config/``), whose ``data.history.chat_history`` is the chat session's whole thread, read from its
newest ``PromptHistory`` row. Queuing it with the journal entry would carry the thread through the
Celery broker on every request. Instead, the response names it with a
:class:`SAMJournalSourceReference`: the source's name, a lookup of the row, the value's path in the
response, and the SHA-256 of the value as the client received it. The value is left out of the queued
entry, and the Celery task reads it back with the source's resolver.

A source is registered by the app that owns its data, with :func:`register_journal_source`, from its
``AppConfig.ready()``, so that the journal never imports the app. A resolver raises
:class:`JournalSourceNotReady` while the row has not been written yet, e.g. because another Celery
task writes it, and the journal's task then retries, for as long as it takes, and
:class:`JournalSourceGone` when the row can never be written, e.g. because its chat session was
deleted. A value that is gone is journaled as :data:`UNRESOLVED_KEY`, with its reference.

**Example**::

    # in the app that owns the data, e.g. smarter.apps.prompt.journal
    def resolve_chat_history(lookup):
        row = PromptHistory.objects.filter(pk=lookup["prompt_history_id"]).first()
        if row is None:
            raise JournalSourceNotReady("PromptHistory is not written yet.")
        return ...

    register_journal_source("prompt.chat_history", resolve_chat_history)

    # in the view
    SmarterJournaledJsonResponse(
        request=request,
        data=data,
        journal_sources=[
            SAMJournalSource(
                name="prompt.chat_history",
                path=("data", "history", "chat_history"),
                lookup={"prompt_history_id": row.pk},
            )
        ],
    )
"""

import hashlib
from collections.abc import Callable, Sequence
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smarter.common.exceptions import SmarterException
from smarter.lib import logging

from .storage import RESERVED_PREFIX, to_json_bytes

logger = logging.getSmarterLogger(__name__)

UNRESOLVED_KEY = RESERVED_PREFIX + "unresolved"
"""The key that stands in for a source's value that could not be read: ``{"$journal:unresolved": <reference>}``."""

JournalSourcePath = tuple[Union[str, int], ...]
"""The keys and indexes from a response's root to a value, e.g. ``("data", "history", "chat_history")``."""

JournalSourceLookup = dict[str, Union[str, int]]
"""The plain values that find a source's row, e.g. ``{"prompt_history_id": 42}``."""

JournalSourceResolver = Callable[[JournalSourceLookup], JsonValue]
"""Reads a source's value, as the client received it, from the database."""


class JournalSourceNotReady(SmarterException):
    """A source's row is not written yet.

    The journal's task retries until it is.
    """

    @property
    def get_formatted_err_message(self):
        """The error message prefix of these errors."""
        return "Smarter Journal Source Not Ready"


class JournalSourceGone(SmarterException):
    """A source's row can never be read, e.g. because it was deleted.

    Its reference is journaled instead.
    """

    @property
    def get_formatted_err_message(self):
        """The error message prefix of these errors."""
        return "Smarter Journal Source Gone"


class SAMJournalSource(BaseModel):
    """A part of a journaled response that the worker reads from the database: what a view passes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., description="The source's name, as it was registered, e.g. prompt.chat_history.")
    path: JournalSourcePath = Field(..., min_length=1, description="The value's path in the response.")
    lookup: JournalSourceLookup = Field(..., description="The plain values that find the source's row.")


class SAMJournalSourceReference(SAMJournalSource):
    """A source, and the SHA-256 of its value as the client received it: what the journal's task receives."""

    digest: str = Field(..., pattern=r"^[a-f0-9]{64}$", description="The SHA-256 of the value's JSON.")


_resolvers: dict[str, JournalSourceResolver] = {}


def register_journal_source(name: str, resolver: JournalSourceResolver) -> None:
    """
    Register a source's resolver, by the source's name.

    Call it from the owning app's ``AppConfig.ready()``, so that the web server and the Celery workers
    both have it. Registering a name again replaces its resolver.

    :param name: The source's name, e.g. ``prompt.chat_history``.
    :param resolver: Returns the value, or raises :class:`JournalSourceNotReady` or :class:`JournalSourceGone`.
    """
    _resolvers[name] = resolver


def value_digest(value: JsonValue) -> str:
    """
    Return the SHA-256 of a value's JSON, as the journal stores it.

    :param value: The value.
    :returns: The digest, as hexadecimal.
    """
    data = to_json_bytes(value)
    return hashlib.sha256(data).hexdigest()


def get_at_path(document: JsonValue, path: JournalSourcePath) -> JsonValue:
    """
    Return the value at a path of a document.

    :param document: The document.
    :param path: The keys and indexes from the document's root.
    :returns: The value.
    :raises KeyError: If the document has no value at the path.
    """
    value = document
    for step in path:
        if isinstance(value, dict) and isinstance(step, str) and step in value:
            value = value[step]
        elif isinstance(value, list) and isinstance(step, int) and 0 <= step < len(value):
            value = value[step]
        else:
            raise KeyError(path)
    return value


def replace_at_path(document: JsonValue, path: JournalSourcePath, value: JsonValue) -> JsonValue:
    """
    Return a copy of a document whose value at a path is replaced.

    Only the dicts and lists on the path are copied, so the original document, e.g. the response that
    is sent to the client, is unchanged.

    :param document: The document, which has a value at the path.
    :param path: The keys and indexes from the document's root.
    :param value: The new value.
    :returns: The new document.
    :raises KeyError: If the document has no value at the path.
    """
    step = path[0]
    rest = path[1:]
    if isinstance(document, dict) and isinstance(step, str) and step in document:
        copied_dict = dict(document)
        if rest:
            copied_dict[step] = replace_at_path(document[step], rest, value)
        else:
            copied_dict[step] = value
        return copied_dict
    if isinstance(document, list) and isinstance(step, int) and 0 <= step < len(document):
        copied_list = list(document)
        if rest:
            copied_list[step] = replace_at_path(document[step], rest, value)
        else:
            copied_list[step] = value
        return copied_list
    raise KeyError(path)


def detach_sources(
    document: JsonValue, sources: Sequence[SAMJournalSource]
) -> tuple[JsonValue, list[SAMJournalSourceReference]]:
    """
    Return a document without its sources' values, and the references that read them back.

    A source whose path the document doesn't have stays in the document, and gets no reference.

    :param document: The response, as JSON.
    :param sources: The sources that the view named.
    :returns: The document, with None at each source's path, and the sources' references.
    """
    references = []
    for source in sources:
        try:
            value = get_at_path(document, source.path)
        except KeyError:
            logger.debug("the response has no %s, which stays in the journal entry", source.name)
            continue
        digest = value_digest(value)
        reference = SAMJournalSourceReference(name=source.name, path=source.path, lookup=source.lookup, digest=digest)
        references.append(reference)
        document = replace_at_path(document, source.path, None)
    return document, references


def resolve_source(reference: SAMJournalSourceReference) -> JsonValue:
    """
    Return a source's value, read from the database.

    :param reference: The source's reference.
    :returns: The value, or ``{"$journal:unresolved": <reference>}`` if it is gone, or isn't the value
        that the client received.
    :raises JournalSourceNotReady: If the source's row is not written yet.
    """
    unresolved: JsonValue = {UNRESOLVED_KEY: reference.model_dump(mode="json")}
    resolver: Optional[JournalSourceResolver] = _resolvers.get(reference.name)
    if resolver is None:
        logger.error("no journal source is registered as %s", reference.name)
        return unresolved
    try:
        value = resolver(dict(reference.lookup))
    except JournalSourceGone as e:
        logger.warning("journal source %s is gone: %s", reference.name, e)
        return unresolved
    if value_digest(value) != reference.digest:
        # the row's value isn't what the client received. Journal the reference, which names what was sent.
        logger.error("journal source %s does not match the response's digest", reference.name)
        return unresolved
    return value


def attach_sources(document: JsonValue, references: Sequence[SAMJournalSourceReference]) -> JsonValue:
    """
    Return a document with its sources' values read back from the database.

    :param document: The document, as :func:`detach_sources` returned it.
    :param references: Its sources' references.
    :returns: The document as the client received it, or with :data:`UNRESOLVED_KEY` where a value is gone.
    :raises JournalSourceNotReady: If a source's row is not written yet.
    """
    for reference in references:
        value = resolve_source(reference)
        document = replace_at_path(document, reference.path, value)
    return document


__all__ = [
    "JournalSourceGone",
    "JournalSourceNotReady",
    "SAMJournalSource",
    "SAMJournalSourceReference",
    "UNRESOLVED_KEY",
    "attach_sources",
    "detach_sources",
    "register_journal_source",
    "resolve_source",
]
