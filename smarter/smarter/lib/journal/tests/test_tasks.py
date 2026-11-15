"""Test the journal's Celery tasks: :mod:`smarter.lib.journal.tasks`."""

from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from unittest.mock import patch

from celery.exceptions import Retry
from django.db import DataError

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.utils import hash_factory
from smarter.lib.journal.models import SAMJournal
from smarter.lib.journal.sources import JournalSourceNotReady, SAMJournalSource
from smarter.lib.journal.tasks import (
    SOURCE_RETRY_MAX_COUNTDOWN,
    SAMJournalEntryRecord,
    create_journal_entry,
    queue_journal_entry,
    source_retry_countdown,
    write_journal_entry,
)


class TestJournalTasks(TestAccountMixin):
    """Test that a queued journal entry is saved once, with the response's key and time."""

    def record(self) -> SAMJournalEntryRecord:
        """A new entry, which is deleted after the test."""
        record = SAMJournalEntryRecord(
            key=hash_factory(length=64),
            created_at=datetime.now(timezone.utc) - timedelta(seconds=30),
            user_id=self.admin_user.pk,
            thing="Guardrail",
            command="apply",
            status_code=HTTPStatus.CREATED,
            request={"url": "http://localhost:9357/api/v1/cli/apply/"},
            response={"data": {"a": 1}},
        )
        self.addCleanup(SAMJournal.objects.filter(key=record.key).delete)
        return record

    def test_write_journal_entry(self):
        """Test that the entry is saved with the record's fields, and the created signal is sent."""
        record = self.record()
        with patch("smarter.lib.journal.tasks.journal_entry_created.send") as created:
            journal = write_journal_entry(record)
        self.assertIsNotNone(journal)
        created.assert_called_once()
        entry = SAMJournal.objects.get(key=record.key)
        self.assertEqual(entry.user, self.admin_user)
        self.assertEqual(entry.created_at, record.created_at)
        self.assertEqual(entry.status_code, HTTPStatus.CREATED)
        self.assertEqual(entry.request, record.request)
        self.assertEqual(entry.response, record.response)

    def test_write_journal_entry_is_idempotent(self):
        """Test that a retry of a saved entry does nothing."""
        record = self.record()
        write_journal_entry(record)
        self.assertIsNone(write_journal_entry(record))
        self.assertEqual(SAMJournal.objects.filter(key=record.key).count(), 1)

    def test_create_journal_entry(self):
        """Test that the task saves the entry from the record's JSON."""
        record = self.record()
        create_journal_entry(record.model_dump(mode="json"))
        self.assertTrue(SAMJournal.objects.filter(key=record.key).exists())

    def test_create_journal_entry_not_retryable(self):
        """Test that an error that won't be retried sends journal_entry_failed, and is raised."""
        record = self.record()
        with (
            patch("smarter.lib.journal.tasks.write_journal_entry", side_effect=DataError("too long")),
            patch("smarter.lib.journal.tasks.journal_entry_failed.send") as failed,
        ):
            with self.assertRaises(DataError):
                create_journal_entry(record.model_dump(mode="json"))
        failed.assert_called_once()
        self.assertEqual(failed.call_args.kwargs["user"], self.admin_user.pk)

    def test_create_journal_entry_retryable(self):
        """Test that an error that will be retried doesn't send journal_entry_failed."""
        record = self.record()
        with (
            patch("smarter.lib.journal.tasks.write_journal_entry", side_effect=ValueError("db down")),
            patch("smarter.lib.journal.tasks.journal_entry_failed.send") as failed,
        ):
            with self.assertRaises(ValueError):
                create_journal_entry(record.model_dump(mode="json"))
        failed.assert_not_called()

    def test_queue_journal_entry(self):
        """Test that the entry is queued as JSON."""
        record = self.record()
        with patch("smarter.lib.journal.tasks.create_journal_entry.delay") as delay:
            queue_journal_entry(record)
        delay.assert_called_once_with(record.model_dump(mode="json"))
        self.assertFalse(SAMJournal.objects.filter(key=record.key).exists())

    def test_queue_journal_entry_without_a_broker(self):
        """Test that an entry that can't be queued is saved now."""
        record = self.record()
        with patch("smarter.lib.journal.tasks.create_journal_entry.delay", side_effect=ConnectionError("no broker")):
            queue_journal_entry(record)
        self.assertTrue(SAMJournal.objects.filter(key=record.key).exists())

    def test_queue_journal_entry_with_sources(self):
        """Test that a source's value is left out of the queued entry, and named instead."""
        record = self.record()
        with patch("smarter.lib.journal.tasks.create_journal_entry.delay") as delay:
            queue_journal_entry(record, [SAMJournalSource(name="test.a", path=("data", "a"), lookup={"id": 1})])
        payload = delay.call_args.args[0]
        self.assertEqual(payload["response"], {"data": {"a": None}})
        self.assertEqual(payload["sources"][0]["name"], "test.a")
        self.assertEqual(record.response, {"data": {"a": 1}})

    def test_queue_journal_entry_with_sources_without_a_broker(self):
        """Test that an entry that can't be queued is saved now, with its sources' values, which it has."""
        record = self.record()
        with patch("smarter.lib.journal.tasks.create_journal_entry.delay", side_effect=ConnectionError("no broker")):
            queue_journal_entry(record, [SAMJournalSource(name="test.a", path=("data", "a"), lookup={"id": 1})])
        self.assertEqual(SAMJournal.objects.get(key=record.key).response, {"data": {"a": 1}})

    def test_create_journal_entry_source_not_ready(self):
        """Test that an entry whose source isn't written yet is retried, with no limit."""
        record = self.record()
        with (
            patch("smarter.lib.journal.tasks.write_journal_entry", side_effect=JournalSourceNotReady("later")),
            patch.object(create_journal_entry, "retry", side_effect=Retry("retried")) as retry,
            patch("smarter.lib.journal.tasks.journal_entry_failed.send") as failed,
        ):
            with self.assertRaises(Retry):
                create_journal_entry(record.model_dump(mode="json"))
        retry.assert_called_once()
        self.assertIsNone(retry.call_args.kwargs["max_retries"])
        self.assertEqual(retry.call_args.kwargs["countdown"], 1)
        failed.assert_not_called()

    def test_source_retry_countdown(self):
        """Test that the wait doubles, up to its limit."""
        countdowns = [source_retry_countdown(retries) for retries in (0, 1, 2, 8, 100)]
        self.assertEqual(countdowns, [1, 2, 4, 256, SOURCE_RETRY_MAX_COUNTDOWN])
