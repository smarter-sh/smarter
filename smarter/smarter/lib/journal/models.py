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

from datetime import timedelta
from typing import Optional, Union

from django.conf import settings
from django.db import models
from django.utils import timezone
from pydantic import JsonValue

from smarter.common.utils import hash_factory
from smarter.lib import logging

from .enum import SmarterJournalCliCommands, SmarterJournalThings
from .storage import (
    BlobReference,
    JournalDocumentDecoder,
    JournalDocumentEncoder,
    blob_references,
    node_references,
    pack,
    unpack,
)

logger = logging.getSmarterLogger(__name__)

DOCUMENT_FIELDS = ("request_document", "response_document")
"""The columns of :class:`SAMJournal` that hold its documents: a query that lists entries defers them."""

BLOB_TOUCH_INTERVAL = timedelta(days=1)
"""A reused blob whose ``last_used_at`` is older than this is touched by :meth:`SAMJournalBlobManager.save_blobs`."""

BLOB_PRUNE_GRACE = timedelta(days=7)
"""An unreferenced blob is pruned only if it was last used longer ago than this.

It must be longer than :data:`BLOB_TOUCH_INTERVAL`, so that a blob that a writer is reusing is never
pruned.
"""

PRUNE_BATCH_SIZE = 1000
"""The number of blobs that :meth:`SAMJournalBlobManager.prune` reads, or deletes, per query."""


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
        Save the blobs that the database doesn't have yet, and touch the stale ones that it has.

        Blobs are content addressed, so a blob that exists already has the same bytes. Another writer
        may save the same blob at the same time: the conflict is ignored.

        A reused blob whose ``last_used_at`` is older than :data:`BLOB_TOUCH_INTERVAL` is touched first,
        so that :meth:`prune` can't delete it before the entry that reuses it is saved. A blob that
        :meth:`prune` deleted before it was touched is not found, and is saved again.

        :param blobs: Each blob's compressed bytes, by digest, from
            :attr:`smarter.lib.journal.storage.JournalDocumentEncoder.blobs`.
        :returns: The number of blobs that were new.
        """
        if not blobs:
            return 0
        digests = list(blobs.keys())
        now = timezone.now()
        stale_before = now - BLOB_TOUCH_INTERVAL
        self.filter(digest__in=digests, last_used_at__lt=stale_before).update(last_used_at=now)
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

    def reachable(self) -> set[str]:
        """
        Return the digests of every blob that a journal entry references, directly or through other blobs.

        Every entry's skeletons are read, and every blob that they reach, once: the whole journal. It
        is meant to run rarely, e.g. weekly, from :meth:`prune`.

        :returns: The digests.
        """
        visited: set[BlobReference] = set()
        reachable: set[str] = set()
        pending: list[BlobReference] = []
        # pages by key, not .iterator(): MySQL's driver would buffer every document at once.
        last_key = ""
        while True:
            entries = SAMJournal.objects.filter(key__gt=last_key).order_by("key")
            page = list(entries.values_list("key", *DOCUMENT_FIELDS)[:PRUNE_BATCH_SIZE])
            if not page:
                break
            for key, request_document, response_document in page:
                last_key = key
                for stored in (request_document, response_document):
                    if stored:
                        skeleton = unpack(stored)
                        pending.extend(blob_references(skeleton))
            self.mark(pending, visited, reachable)
        return reachable

    def mark(self, pending: list[BlobReference], visited: set[BlobReference], reachable: set[str]) -> None:
        """
        Mark the pending blobs reachable, and every blob that they reference, reading them in batches.

        A blob is visited once as a plain blob and once as a chain's node, because the two read its
        value differently.

        :param pending: The blobs to mark, which this empties.
        :param visited: The blobs already marked, which this extends.
        :param reachable: The digests of the blobs already marked, which this extends.
        """
        while pending:
            batch: list[BlobReference] = []
            while pending and len(batch) < PRUNE_BATCH_SIZE:
                reference = pending.pop()
                if reference in visited:
                    continue
                visited.add(reference)
                reachable.add(reference[0])
                batch.append(reference)
            digests = [digest for digest, _ in batch]
            loaded = dict(self.filter(digest__in=digests).values_list("digest", "data"))
            for digest, is_node in batch:
                data = loaded.get(digest)
                if data is None:
                    logger.error("an entry references the missing journal blob %s", digest)
                    continue
                value = unpack(data)
                if is_node:
                    pending.extend(node_references(value))
                else:
                    pending.extend(blob_references(value))

    def prune(self, grace: timedelta = BLOB_PRUNE_GRACE, dry_run: bool = False) -> int:
        """
        Delete the blobs that no journal entry references, and that weren't used within ``grace``.

        The journal's entries are deleted only when their user is, or by hand, so there is little to
        prune. Mark and sweep suits that: nothing is counted on each write. A writer may reuse an
        unreferenced blob while this runs, so the delete itself requires ``last_used_at`` to be older
        than ``grace``, which a reused blob isn't (see :meth:`save_blobs`).

        :param grace: How long an unreferenced blob is kept after its last use.
        :param dry_run: If True, count the blobs that would be deleted, and delete none.
        :returns: The number of blobs deleted, or that would be.
        :raises ValueError: If ``grace`` isn't longer than :data:`BLOB_TOUCH_INTERVAL`.
        """
        if grace <= BLOB_TOUCH_INTERVAL:
            raise ValueError(f"grace must be longer than {BLOB_TOUCH_INTERVAL}, which is {grace}.")
        cutoff = timezone.now() - grace
        reachable = self.reachable()
        unreferenced = []
        last_digest = ""
        while True:
            old_blobs = self.filter(last_used_at__lt=cutoff, digest__gt=last_digest).order_by("digest")
            page = list(old_blobs.values_list("digest", flat=True)[:PRUNE_BATCH_SIZE])
            if not page:
                break
            last_digest = page[-1]
            for digest in page:
                if digest not in reachable:
                    unreferenced.append(digest)
        if dry_run:
            logger.info("%s unreferenced journal blobs would be deleted", len(unreferenced))
            return len(unreferenced)
        deleted = 0
        for start in range(0, len(unreferenced), PRUNE_BATCH_SIZE):
            batch = unreferenced[start : start + PRUNE_BATCH_SIZE]
            count, _ = self.filter(digest__in=batch, last_used_at__lt=cutoff).delete()
            deleted += count
        logger.info("deleted %s unreferenced journal blobs, of %s reachable", deleted, len(reachable))
        return deleted


class SAMJournalBlob(models.Model):
    """
    A part of one or more journal entries' documents: a large dict or string, or one item of a long list.

    Its primary key is the SHA-256 of its JSON, so each part is stored once, however many entries
    contain it. Its data never changes. It is not deleted with the entries that reference it, but by
    :meth:`SAMJournalBlobManager.prune`, once no entry references it.

    See :mod:`smarter.lib.journal.storage`.
    """

    digest = models.CharField(primary_key=True, max_length=64, editable=False)
    data = models.BinaryField(help_text="The blob's JSON, compressed with zlib.")
    last_used_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When an entry last saved or reused the blob, to within a day. See SAMJournalBlobManager.prune.",
    )

    objects = SAMJournalBlobManager()

    def __str__(self) -> str:
        """
        Return the blob's digest.

        :returns: The digest, 64 hexadecimal characters.
        """
        digest = str(self.digest)
        return digest


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
    #: The id of :attr:`user`, which Django adds: None for an anonymous request.
    user_id: Optional[int]
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

    #: The documents that were given to, or read from, this instance, by name: see :meth:`documents`.
    #: Declared here, not in ``__init__``, which a Django model doesn't override. Not a field.
    _journal_documents: Optional[dict[str, JsonValue]] = None

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
        documents = self._journal_documents
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
