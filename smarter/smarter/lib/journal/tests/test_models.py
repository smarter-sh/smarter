"""Test the journal's models: :mod:`smarter.lib.journal.models`."""

from http import HTTPStatus

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.utils import hash_factory
from smarter.lib.journal.models import SAMJournal, SAMJournalBlob
from smarter.lib.journal.storage import JournalDocumentEncoder, JournalStorageError


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
