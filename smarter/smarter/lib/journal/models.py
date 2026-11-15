"""
The Django models of the Smarter Journal, the audit log of the Smarter api's requests and responses.

Each :class:`SAMJournal` entry is queued by
:class:`~smarter.lib.journal.http.SmarterJournaledJsonResponse` while the ``ENABLE_JOURNAL``
switch is on, and written by a Celery task, :func:`smarter.lib.journal.tasks.create_journal_entry`.

The journal is insert-only, and read only to investigate a rare incident, so its storage is designed
for writing: an entry's request and response documents are stored as compressed skeletons, whose
large and repeated parts are :class:`SAMJournalBlob` rows that every entry shares. See
:mod:`smarter.lib.journal.storage`.
"""

from typing import Optional, Union

from django.conf import settings
from django.db import models
from django.utils import timezone
from pydantic import JsonValue

from smarter.common.utils import hash_factory

from .enum import SmarterJournalCliCommands, SmarterJournalThings
from .storage import (
    JournalDocumentDecoder,
    JournalDocumentEncoder,
    pack,
    unpack,
)

DOCUMENT_FIELDS = ("request_document", "response_document")
"""The columns of :class:`SAMJournal` that hold its documents: a query that lists entries defers them."""


class SAMJournalManager(models.Manager["SAMJournal"]):
    """The manager of :class:`SAMJournal`."""

    def create_entry(self, request: JsonValue, response: JsonValue, **fields) -> "SAMJournal":
        """
        Create a journal entry with its documents.

        ``SAMJournal.objects.create(request=..., response=...)`` does the same, but type checkers don't
        know the documents, which are properties, not fields.

        :param request: The serialized http request.
        :param response: The response's JSON body.
        :param fields: The entry's other fields, e.g. ``user``, ``thing``, ``command``, ``status_code``.
        :returns: The saved entry.
        """
        entry = self.model(**fields)
        entry.request = request
        entry.response = response
        entry.save(force_insert=True)
        return entry


class SAMJournalBlobManager(models.Manager["SAMJournalBlob"]):
    """The manager of :class:`SAMJournalBlob`, which saves new blobs and reads them."""

    def save_blobs(self, blobs: dict[str, bytes]) -> int:
        """
        Save the blobs that the database doesn't have yet.

        Blobs are content addressed, so a blob that exists already has the same bytes. Another writer
        may save the same blob at the same time: the conflict is ignored.

        :param blobs: Each blob's compressed bytes, by digest, from
            :attr:`smarter.lib.journal.storage.JournalDocumentEncoder.blobs`.
        :returns: The number of blobs that were new.
        """
        if not blobs:
            return 0
        digests = list(blobs.keys())
        existing_digests = self.filter(digest__in=digests).values_list("digest", flat=True)
        existing = set(existing_digests)
        new_blobs = []
        for digest in digests:
            if digest in existing:
                continue
            blob = self.model(digest=digest, data=blobs[digest])
            new_blobs.append(blob)
        self.bulk_create(new_blobs, ignore_conflicts=True, batch_size=500)
        return len(new_blobs)

    def read_blob(self, digest: str) -> bytes:
        """
        Return a blob's compressed bytes.

        :param digest: The blob's digest.
        :returns: Its bytes.
        :raises KeyError: If there is no such blob.
        """
        try:
            blob = self.get(digest=digest)
        except self.model.DoesNotExist as e:
            raise KeyError(digest) from e
        return bytes(blob.data)


class SAMJournalBlob(models.Model):
    """
    A part of one or more journal entries' documents: a large dict or string, or one item of a long list.

    Its primary key is the SHA-256 of its JSON, so each part is stored once, however many entries
    contain it. A blob is never changed, and is not deleted with the entries that reference it.

    See :mod:`smarter.lib.journal.storage`.
    """

    digest = models.CharField(primary_key=True, max_length=64, editable=False)
    data = models.BinaryField(help_text="The blob's JSON, compressed with zlib.")

    objects = SAMJournalBlobManager()

    def __str__(self) -> str:
        return self.digest


class SAMJournal(models.Model):
    """
    Model representing a journal entry: one request to the Smarter api, and its response.

    Every request that is answered with a :class:`~smarter.lib.journal.http.SmarterJournaledJsonResponse`
    is journaled while the ``ENABLE_JOURNAL`` switch is on, whether it is a cli command (``api/v1/cli``),
    an LLMClient's prompt, or a console api. Each journal entry records the user responsible, the kind of
    entity affected, the command executed, the request and response documents, and the status code.

    The documents are read and written as JSON through :attr:`request` and :attr:`response`. They are
    stored in :attr:`request_document` and :attr:`response_document`, as compressed skeletons whose
    large and repeated parts are :class:`SAMJournalBlob` rows.

    **Example:**

    Creating a new journal entry::

        entry = SAMJournal.objects.create_entry(
            user=request.user,
            thing=SmarterJournalThings.PROMPT.value,
            command=SmarterJournalCliCommands.CREATE.value,
            request={"data": "example"},
            response={"result": "success"},
            status_code=201
        )

    **See also:**

    - :mod:`smarter.lib.journal.storage`: how the documents are stored.
    - :func:`smarter.common.utils.hash_factory`: generates unique keys for journal entries.
    - :class:`smarter.lib.journal.enum.SmarterJournalCliCommands`: the valid CLI commands for journal entries.
    - :class:`smarter.lib.journal.enum.SmarterJournalThings`: the valid entity types for journal entries.
    """

    key = models.CharField(primary_key=True, default=None, editable=False, max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, db_index=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True, db_index=True)
    thing = models.CharField(
        max_length=24, choices=SmarterJournalThings.choices(), default=SmarterJournalThings.PROMPT.value, blank=True
    )
    command = models.CharField(
        max_length=24,
        choices=SmarterJournalCliCommands.choices(),
        blank=True,
        default=SmarterJournalCliCommands.PROMPT.value,
    )
    request_document = models.BinaryField(
        help_text="The request's skeleton, compressed. See smarter.lib.journal.storage."
    )
    response_document = models.BinaryField(
        help_text="The response's skeleton, compressed. See smarter.lib.journal.storage."
    )
    status_code = models.PositiveSmallIntegerField(default=200)

    objects = SAMJournalManager()

    @property
    def request(self) -> JsonValue:
        """The serialized http request, as JSON."""
        return self.read_document("request", self.request_document)

    @request.setter
    def request(self, value: JsonValue) -> None:
        self.documents()["request"] = value

    @property
    def response(self) -> JsonValue:
        """The response's JSON body."""
        return self.read_document("response", self.response_document)

    @response.setter
    def response(self, value: JsonValue) -> None:
        self.documents()["response"] = value

    def documents(self) -> dict[str, JsonValue]:
        """
        Return the documents that were given or read, by name: ``request`` and ``response``.

        :returns: The documents, a dict of this instance.
        """
        documents: Optional[dict[str, JsonValue]] = getattr(self, "_journal_documents", None)
        if documents is None:
            documents = {}
            self._journal_documents = documents
        return documents

    def read_document(self, name: str, stored: Optional[Union[bytes, memoryview]]) -> JsonValue:
        """
        Return a document: the one given, or the one stored, read once.

        :param name: The document's name, ``request`` or ``response``.
        :param stored: The document's compressed skeleton, or empty if the entry has none yet.
        :returns: The document.
        :raises smarter.lib.journal.storage.JournalStorageError: If a blob of the document is missing.
        """
        documents = self.documents()
        if name in documents:
            return documents[name]
        document: JsonValue = None
        if stored:
            skeleton = unpack(stored)
            decoder = JournalDocumentDecoder(SAMJournalBlob.objects.read_blob)
            document = decoder.decode(skeleton)
        documents[name] = document
        return document

    def save(self, *args, **kwargs):
        """
        Save the entry, giving it a random 64-character key if it has none.

        The documents given to :attr:`request` and :attr:`response` are encoded, and their new blobs are
        saved before the entry, so that a saved entry never references a missing blob.

        :param args: Passed to Django's ``save()``.
        :param kwargs: Passed to Django's ``save()``.
        """
        if not self.key:
            self.key = hash_factory(length=64)
        documents = self.documents()
        encoder = JournalDocumentEncoder()
        # an entry saved without a document stores JSON null for it.
        if "request" in documents or not self.request_document:
            request_skeleton = encoder.encode(documents.get("request"))
            self.request_document = pack(request_skeleton)
        if "response" in documents or not self.response_document:
            response_skeleton = encoder.encode(documents.get("response"))
            self.response_document = pack(response_skeleton)
        SAMJournalBlob.objects.save_blobs(encoder.blobs)
        super().save(*args, **kwargs)
