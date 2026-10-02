"""The documents of a vectorstore: the text that is split, embedded, and loaded into it."""

from django.db import models

from smarter.lib.django.models import TimestampedModel

from .vectorstore_meta import VectorstoreMeta

PAGE_BREAK = "\f"
"""Separates the pages of a document's content, e.g. of a PDF, so that each chunk records its page."""


class VectorstoreDocumentSource(models.TextChoices):
    """Where a document came from."""

    UPLOAD = "upload", "Upload"
    URL = "url", "URL"
    TEXT = "text", "Text"
    FILE = "file", "File"


class VectorstoreDocumentStatus(models.TextChoices):
    """
    The lifecycle of a document.

    - pending: its text is stored, and waits to be loaded.
    - loading: it is being split, embedded and loaded.
    - loaded: its chunks are in the vector database.
    - failed: see status_message.
    - deleting: its chunks are being removed from the vector database, then it is deleted.
    """

    PENDING = "pending", "Pending"
    LOADING = "loading", "Loading"
    LOADED = "loaded", "Loaded"
    FAILED = "failed", "Failed"
    DELETING = "deleting", "Deleting"


class VectorstoreDocument(TimestampedModel):
    """
    A document of a vectorstore, e.g. a PDF.

    Its text is extracted when it is added, and kept here, rather than the original file, so
    that proprietary documents are never written to file storage, and so that a document can
    be loaded again, e.g. after the embeddings model changes. Its chunks are loaded into the
    vector database with deterministic ids, :meth:`chunk_id`, so that they can be replaced
    and removed.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Vectorstore Document"
        verbose_name_plural = "Vectorstore Documents"
        unique_together = ("vectorstore", "sha256")

    vectorstore = models.ForeignKey(VectorstoreMeta, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=255, help_text="e.g. a file name, or a URL.")
    source = models.CharField(max_length=10, choices=VectorstoreDocumentSource.choices)
    content_type = models.CharField(max_length=100, blank=True, default="")
    content = models.TextField(help_text="The extracted text. Pages are separated by form feeds.")
    sha256 = models.CharField(max_length=64, help_text="Of the content, so that a document is not loaded twice.")
    size_bytes = models.PositiveBigIntegerField(default=0, help_text="Of the original file.")
    metadata = models.JSONField(default=dict, blank=True, help_text="Stored with each chunk, for filtered search.")
    status = models.CharField(
        max_length=10, choices=VectorstoreDocumentStatus.choices, default=VectorstoreDocumentStatus.PENDING
    )
    status_message = models.TextField(blank=True, default="")
    chunk_count = models.PositiveIntegerField(default=0, help_text="The number of chunks in the vector database.")
    loaded_at = models.DateTimeField(null=True, blank=True)

    @property
    def pages(self) -> list[str]:
        return self.content.split(PAGE_BREAK)

    def chunk_id(self, index: int) -> str:
        """
        The id of a chunk in the vector database.

        Qdrant requires a UUID or an integer, so the id is a UUID derived from the document and
        the chunk's index.
        """
        # pylint: disable=C0415
        import uuid

        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"smarter:vectorstore:{self.vectorstore_id}:{self.pk}:{index}"))  # type: ignore[attr-defined]

    def chunk_ids(self, count: int = 0) -> list[str]:
        return [self.chunk_id(i) for i in range(count or self.chunk_count)]

    def __str__(self):
        return f"{self.vectorstore.name}: {self.name} ({self.status})"


__all__ = ["VectorstoreDocument", "VectorstoreDocumentSource", "VectorstoreDocumentStatus", "PAGE_BREAK"]
