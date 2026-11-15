"""Test the journal's models: :mod:`smarter.lib.journal.models`."""

from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.utils import hash_factory
from smarter.lib.journal.models import BLOB_TOUCH_INTERVAL, SAMJournal, SAMJournalBlob
from smarter.lib.journal.storage import JournalDocumentEncoder, JournalStorageError
from smarter.lib.journal.tasks import prune_journal_blobs


class TestSAMJournal(TestAccountMixin):
    """Test that an entry's documents are stored as skeletons and blobs, and read back."""

    def create(self, request, response) -> SAMJournal:
        """Create an entry, and delete it, and its blobs, after the test."""
        entry = SAMJournal.objects.create_entry(
            user=self.admin_user,
            thing="LLMClient",
            command="prompt",
            request=request,
            response=response,
            status_code=HTTPStatus.OK,
        )
        self.addCleanup(SAMJournal.objects.filter(key=entry.key).delete)
        encoder = JournalDocumentEncoder()
        encoder.encode(request)
        encoder.encode(response)
        digests = list(encoder.blobs)
        self.addCleanup(SAMJournalBlob.objects.filter(digest__in=digests).delete)
        return entry

    def unique_text(self) -> str:
        """A long string that no other test stores."""
        return hash_factory(length=64) * 40

    def test_documents_round_trip(self):
        """Test that the documents read from the database are the ones given."""
        request = {"url": "http://localhost:9357/api/v1/prompt/", "META": {"HTTP_HOST": "localhost"}}
        response = {"data": {"messages": [{"content": self.unique_text()}] * 3, "system": self.unique_text()}}
        entry = self.create(request, response)
        self.assertEqual(len(entry.key), 64)
        reread = SAMJournal.objects.get(key=entry.key)
        self.assertEqual(reread.request, request)
        self.assertEqual(reread.response, response)

    def test_blobs_are_shared(self):
        """Test that two entries with the same large part store it once."""
        shared = self.unique_text()
        self.create({}, {"a": shared})
        before = SAMJournalBlob.objects.count()
        self.create({}, {"b": shared})
        self.assertEqual(SAMJournalBlob.objects.count(), before)

    def test_save_blobs(self):
        """Test that save_blobs() saves only the blobs that are new."""
        encoder = JournalDocumentEncoder()
        encoder.encode({"x": self.unique_text(), "y": self.unique_text()})
        digests = list(encoder.blobs)
        self.addCleanup(SAMJournalBlob.objects.filter(digest__in=digests).delete)
        self.assertEqual(SAMJournalBlob.objects.save_blobs(encoder.blobs), 2)
        self.assertEqual(SAMJournalBlob.objects.save_blobs(encoder.blobs), 0)
        self.assertEqual(SAMJournalBlob.objects.save_blobs({}), 0)
        blob = SAMJournalBlob.objects.get(digest=digests[0])
        self.assertEqual(str(blob), digests[0])

    def test_read_blob(self):
        """Test that read_blob() raises KeyError for a missing blob, which the decoder reports."""
        with self.assertRaises(KeyError):
            SAMJournalBlob.objects.read_blob("0" * 64)
        entry = self.create({}, {"a": self.unique_text()})
        SAMJournalBlob.objects.all().filter(digest__in=self.blob_digests(entry)).delete()
        reread = SAMJournal.objects.get(key=entry.key)
        with self.assertRaises(JournalStorageError):
            _ = reread.response

    def blob_digests(self, entry: SAMJournal) -> list[str]:
        """The digests of an entry's response's blobs."""
        encoder = JournalDocumentEncoder()
        encoder.encode(entry.response)
        return list(encoder.blobs)

    def test_entry_without_documents(self):
        """Test that an entry saved without documents stores JSON null for them."""
        entry = SAMJournal(thing="Guardrail", command="get")
        entry.save()
        self.addCleanup(SAMJournal.objects.filter(key=entry.key).delete)
        reread = SAMJournal.objects.get(key=entry.key)
        self.assertIsNone(reread.request)
        self.assertIsNone(reread.response)

    def test_documents_are_read_once(self):
        """Test that an entry decodes each document once."""
        entry = self.create({}, {"a": self.unique_text()})
        reread = SAMJournal.objects.get(key=entry.key)
        first = reread.response
        reread.response_document = None
        self.assertIs(reread.response, first)


class TestSAMJournalBlobPrune(TestAccountMixin):
    """Test that prune() deletes only the old blobs that no entry references, and never one that is being reused."""

    def document(self) -> dict:
        """A document of blobs, a chain whose items reference blobs, and an escaped dict, that no other test has."""
        unique = hash_factory(length=64)
        return {
            "text": unique * 40,
            "thread": [{"content": f"{unique} {i} " * 30, "long": f"{unique}{i}" * 40} for i in range(5)],
        }

    def digests(self, document) -> list[str]:
        """The digests of a document's blobs, which are deleted after the test."""
        encoder = JournalDocumentEncoder()
        encoder.encode(document)
        digests = list(encoder.blobs)
        self.addCleanup(SAMJournalBlob.objects.filter(digest__in=digests).delete)
        return digests

    def age(self, digests: list[str], days: int) -> None:
        """Make blobs look last used ``days`` ago."""
        last_used_at = timezone.now() - timedelta(days=days)
        SAMJournalBlob.objects.filter(digest__in=digests).update(last_used_at=last_used_at)

    def entry(self, document) -> SAMJournal:
        """An entry whose response is the document, deleted after the test."""
        entry = SAMJournal.objects.create_entry(request={}, response=document, thing="Guardrail", command="get")
        self.addCleanup(SAMJournal.objects.filter(key=entry.key).delete)
        return entry

    def test_prune(self):
        """Test that old unreferenced blobs are deleted, and referenced or recently used ones are kept."""
        kept_document = self.document()
        kept = self.digests(kept_document)
        entry = self.entry(kept_document)
        orphaned_document = self.document()
        orphaned = self.digests(orphaned_document)
        orphan = self.entry(orphaned_document)
        orphan.delete()
        recent_document = self.document()
        recent = self.digests(recent_document)
        recent_entry = self.entry(recent_document)
        recent_entry.delete()
        self.age(kept + orphaned, days=30)
        self.assertEqual(SAMJournalBlob.objects.prune(dry_run=True), len(orphaned))
        self.assertEqual(SAMJournalBlob.objects.filter(digest__in=orphaned).count(), len(orphaned))
        self.assertEqual(SAMJournalBlob.objects.prune(), len(orphaned))
        self.assertFalse(SAMJournalBlob.objects.filter(digest__in=orphaned).exists())
        self.assertEqual(SAMJournalBlob.objects.filter(digest__in=kept).count(), len(kept))
        self.assertEqual(SAMJournalBlob.objects.filter(digest__in=recent).count(), len(recent))
        # the kept entry still reads back whole.
        self.assertEqual(SAMJournal.objects.get(key=entry.key).response, kept_document)

    def test_reuse_touches_stale_blobs(self):
        """Test that saving an entry that reuses old blobs touches them, so that prune() keeps them."""
        document = self.document()
        digests = self.digests(document)
        first = self.entry(document)
        first.delete()
        self.age(digests, days=30)
        self.entry(document)
        touched = SAMJournalBlob.objects.filter(
            digest__in=digests, last_used_at__gte=timezone.now() - timedelta(hours=1)
        )
        self.assertEqual(touched.count(), len(digests))
        self.age(digests, days=30)
        self.assertEqual(SAMJournalBlob.objects.filter(digest__in=digests).count(), len(digests))
        SAMJournalBlob.objects.prune()
        self.assertEqual(SAMJournalBlob.objects.filter(digest__in=digests).count(), len(digests))

    def test_reuse_races_prune(self):
        """Test that a blob that prune() is about to delete, when a writer reuses it, is not deleted."""
        document = self.document()
        digests = self.digests(document)
        entry = self.entry(document)
        entry.delete()
        self.age(digests, days=30)
        manager = SAMJournalBlob.objects
        real_reachable = manager.reachable

        def reachable_then_reuse():
            # prune() has found the blobs unreferenced, and a writer reuses them before it deletes them.
            found = real_reachable()
            self.entry(document)
            return found

        with patch.object(manager, "reachable", side_effect=reachable_then_reuse):
            manager.prune()
        self.assertEqual(manager.filter(digest__in=digests).count(), len(digests))

    def test_blob_deleted_before_reuse_is_saved_again(self):
        """Test that a writer saves again a blob that prune() deleted, when it reuses it."""
        document = self.document()
        digests = self.digests(document)
        first = self.entry(document)
        first.delete()
        self.age(digests, days=30)
        SAMJournalBlob.objects.prune()
        self.assertFalse(SAMJournalBlob.objects.filter(digest__in=digests).exists())
        entry = self.entry(document)
        self.assertEqual(SAMJournal.objects.get(key=entry.key).response, document)

    def test_missing_blob_is_logged(self):
        """Test that marking an entry whose blob is missing logs it, and goes on."""
        document = self.document()
        digests = self.digests(document)
        entry = self.entry(document)
        SAMJournalBlob.objects.filter(digest__in=digests).delete()
        with patch("smarter.lib.journal.models.logger") as logger:
            reachable = SAMJournalBlob.objects.reachable()
        self.assertTrue(set(digests) & reachable)
        logger.error.assert_called()
        entry.delete()

    def test_grace_must_exceed_touch_interval(self):
        """Test that a grace that a reused blob might not be touched within is refused."""
        with self.assertRaises(ValueError):
            SAMJournalBlob.objects.prune(grace=BLOB_TOUCH_INTERVAL)

    def test_task_and_command(self):
        """Test the Celery task and the management command."""
        document = self.document()
        digests = self.digests(document)
        self.entry(document).delete()
        self.age(digests, days=30)
        call_command("prune_journal_blobs", "--dry-run")
        self.assertEqual(SAMJournalBlob.objects.filter(digest__in=digests).count(), len(digests))
        with self.assertRaises(SystemExit):
            call_command("prune_journal_blobs", "--grace-days", "1")
        call_command("prune_journal_blobs")
        self.assertFalse(SAMJournalBlob.objects.filter(digest__in=digests).exists())
        self.assertEqual(prune_journal_blobs(), 0)
