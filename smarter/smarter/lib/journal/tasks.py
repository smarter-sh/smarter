"""
Celery tasks of the Smarter Journal.

A journaled response doesn't write its journal entry: it queues :func:`create_journal_entry`, with a
:class:`SAMJournalEntryRecord`, and returns. Encoding and saving the entry's documents happens in a
Celery worker, off the request's thread.

The parts of a response that Smarter has already saved, e.g. an LLMClient configuration's chat
thread, are not queued: the record names them with references (see :mod:`smarter.lib.journal.sources`),
and the task reads them from the database. Their rows may be written by other Celery tasks, so while
one is missing, the task retries, with a backoff of up to :data:`SOURCE_RETRY_MAX_COUNTDOWN` seconds,
for as long as it takes.

The entry's key is chosen before it is queued, so that the response can return it in its metadata.
The task is idempotent: a retry of an entry that was saved does nothing.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Optional

from django.db import DataError
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .contract.const import JOURNAL_KEY_PATTERN
from .models import BLOB_PRUNE_GRACE, SAMJournal, SAMJournalBlob
from .signals import journal_entry_created, journal_entry_failed
from .sources import (
    JournalSourceNotReady,
    SAMJournalSource,
    SAMJournalSourceReference,
    attach_sources,
    detach_sources,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING])
error_logger = logging.getSmarterLogger(__name__)
"""Logs whatever the waffle switches, for a journal entry that could not be saved."""

NOT_RETRYABLE = (DataError,)
"""Errors that fail the same way on every retry, e.g. a value too long for its column."""

SOURCE_RETRY_MAX_COUNTDOWN = 300
"""The longest wait, in seconds, between two tries of an entry whose source's row is not written yet."""


def source_retry_countdown(retries: int) -> int:
    """
    Return how long to wait before the next try of an entry whose source is not ready.

    :param retries: The number of tries so far.
    :returns: 1, 2, 4, ... seconds, up to :data:`SOURCE_RETRY_MAX_COUNTDOWN`.
    """
    exponent = min(retries, 16)
    countdown = 2**exponent
    return min(countdown, SOURCE_RETRY_MAX_COUNTDOWN)


class SAMJournalEntryRecord(BaseModel):
    """
    A journal entry, as it is queued: the fields of a :class:`~smarter.lib.journal.models.SAMJournal` row.

    It travels through the Celery broker as JSON, so the user is its id, and the documents are JSON.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., pattern=JOURNAL_KEY_PATTERN, description="SAMJournal.key, chosen by the response.")
    created_at: datetime = Field(..., description="When the response was made, not when the entry was saved.")
    user_id: Optional[int] = Field(
        None, description="SAMJournal.user: the user's id, or null for an anonymous request."
    )
    thing: str = Field(..., description="SAMJournal.thing, blank if the response has none.")
    command: str = Field(..., description="SAMJournal.command, blank if the response has none.")
    status_code: int = Field(..., ge=0, le=65535, description="SAMJournal.status_code: the http status.")
    request: JsonValue = Field(..., description="SAMJournal.request: the serialized http request.")
    response: JsonValue = Field(
        ..., description="SAMJournal.response: the response's JSON body, with None at each source's path."
    )
    sources: list[SAMJournalSourceReference] = Field(
        default_factory=list, description="The parts of the response that the task reads from the database."
    )


def write_journal_entry(record: SAMJournalEntryRecord) -> Optional[SAMJournal]:
    """
    Save a journal entry, unless it is saved already, and send ``journal_entry_created``.

    The record's sources are read from the database first.

    :param record: The entry.
    :returns: The new entry, or None if an entry with its key existed.
    :raises JournalSourceNotReady: If a source's row is not written yet.
    """
    if SAMJournal.objects.filter(key=record.key).exists():
        logger.debug("journal entry %s exists already", record.key)
        return None
    response = attach_sources(record.response, record.sources)
    journal = SAMJournal.objects.create_entry(
        key=record.key,
        created_at=record.created_at,
        user_id=record.user_id,
        thing=record.thing,
        command=record.command,
        status_code=record.status_code,
        request=record.request,
        response=response,
    )
    journal_entry_created.send(sender=SAMJournal, journal=journal)
    return journal


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    dont_autoretry_for=NOT_RETRYABLE,
    retry_backoff=smarter_settings.app_llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.app_llmclient_tasks_celery_max_retries,
    queue=smarter_settings.app_llmclient_tasks_celery_task_queue,
)
def create_journal_entry(self, record: dict[str, JsonValue]) -> None:
    """
    Celery task: save a journal entry.

    While a source's row is not written yet, the task is retried, with no limit. Other errors are
    retried up to the configured limit. When the entry can't be saved, and won't be retried,
    ``journal_entry_failed`` is sent, whose receiver logs the gap in the journal at ERROR.

    :param self: The task, which is bound.
    :param record: The entry, a :class:`SAMJournalEntryRecord` as JSON.
    """
    entry = SAMJournalEntryRecord.model_validate(record)
    try:
        write_journal_entry(entry)
    except JournalSourceNotReady as e:
        retries = self.request.retries
        countdown = source_retry_countdown(retries)
        logger.debug(
            "journal entry %s waits %ss for its source: %s",
            entry.key,
            countdown,
            e,
        )
        raise self.retry(exc=e, countdown=countdown, max_retries=None)
    except Exception as e:
        is_final = isinstance(e, NOT_RETRYABLE) or self.request.retries >= self.max_retries
        if is_final:
            journal_entry_failed.send(
                sender=SAMJournal,
                user=entry.user_id,
                thing=entry.thing,
                command=entry.command,
                status=entry.status_code,
                request=None,
                response=None,
                error=e,
            )
        raise


def queue_journal_entry(record: SAMJournalEntryRecord, sources: Sequence[SAMJournalSource] = ()) -> None:
    """
    Queue a journal entry, to be saved by a Celery worker.

    The values of the response's sources are left out of the queued entry, which names them instead,
    so that data that Smarter has already saved doesn't pass through the broker.

    If the entry can't be queued, e.g. because the broker is down, the whole entry is saved now
    instead: the response is slower, but the journal has no gap.

    :param record: The entry, with its whole response.
    :param sources: The parts of the response that the worker reads from the database.
    :raises Exception: Whatever saving the entry raised, if it couldn't be queued nor saved.
    """
    response, references = detach_sources(record.response, sources)
    queued = record.model_copy(update={"response": response, "sources": references})
    payload = queued.model_dump(mode="json")
    try:
        create_journal_entry.delay(payload)
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_logger.warning(
            "could not queue journal entry %s, and is saving it now: %s",
            record.key,
            type(e).__name__,
        )
        write_journal_entry(record)
        return
    logger.debug("queued journal entry %s", record.key)


@app.task(queue=smarter_settings.app_llmclient_tasks_celery_task_queue)
def prune_journal_blobs(grace_days: int = BLOB_PRUNE_GRACE.days) -> int:
    """
    Celery task: delete the journal's blobs that no entry references.

    Celery Beat runs it weekly.

    :param grace_days: How many days an unreferenced blob is kept after its last use.
    :returns: The number of blobs deleted.
    """
    grace = timedelta(days=grace_days)
    deleted = SAMJournalBlob.objects.prune(grace=grace)
    return deleted


__all__ = [
    "SAMJournalEntryRecord",
    "prune_journal_blobs",
    "SOURCE_RETRY_MAX_COUNTDOWN",
    "create_journal_entry",
    "queue_journal_entry",
    "write_journal_entry",
]
