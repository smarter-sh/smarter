"""The dumps of a vectorstore: Qdrant snapshots, and Pinecone backups."""

from django.db import models

from smarter.lib.django.models import TimestampedModel

from .vectorstore_meta import VectorstoreMeta


class VectorstoreSnapshotStatus(models.TextChoices):
    """The lifecycle of a snapshot."""

    CREATING = "creating", "Creating"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class VectorstoreSnapshot(TimestampedModel):
    """
    A dump of a vectorstore's database, kept where the backend keeps it.

    A self-hosted Qdrant snapshot is a file on the database's own volume. A Pinecone backup is
    kept by Pinecone. Celery Beat takes them on the schedule of the manifest's
    ``spec.maintenance``, and prunes the oldest beyond its retention.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Vectorstore Snapshot"
        verbose_name_plural = "Vectorstore Snapshots"
        ordering = ["-created_at"]

    vectorstore = models.ForeignKey(VectorstoreMeta, on_delete=models.CASCADE, related_name="snapshots")
    name = models.CharField(max_length=255, help_text="The snapshot's name, or the backup's id, in the backend.")
    status = models.CharField(
        max_length=10, choices=VectorstoreSnapshotStatus.choices, default=VectorstoreSnapshotStatus.CREATING
    )
    status_message = models.TextField(blank=True, default="")
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    vector_count = models.BigIntegerField(null=True, blank=True, help_text="At the time of the snapshot.")
    scheduled = models.BooleanField(default=True, help_text="Taken by Celery Beat, rather than on request.")

    def __str__(self):
        return f"{self.vectorstore.name}: {self.name} ({self.status})"


__all__ = ["VectorstoreSnapshot", "VectorstoreSnapshotStatus"]
