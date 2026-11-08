"""
A user's data export: the manifest of every resource that they own, zipped and emailed to them.

The user menu's Download My Data starts one, and the web console shows its progress, step by step, from
this row, which the Celery task :func:`smarter.apps.account.tasks.create_data_export` updates as it works.
See :mod:`smarter.apps.account.data_export`.
"""

from datetime import datetime, timedelta
from typing import Optional

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from smarter.lib.django.models import TimestampedModel

DATA_EXPORT_STALE_AFTER = timedelta(minutes=15)
"""An export that has neither finished nor failed after this long is abandoned, e.g. its worker restarted.

A user may then start another.
"""


class DataExportStatus(models.TextChoices):
    """Where a data export is in its life."""

    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class DataExportStep(models.TextChoices):
    """
    The step that a data export is on, in the order that it takes them.

    The web console illustrates each one. ``done`` follows the last step of an export that succeeded.
    """

    QUEUED = "queued", "Waiting for a worker"
    INVENTORY = "inventory", "Finding every resource that the user owns"
    MANIFESTS = "manifests", "Writing each resource's manifest"
    ARCHIVE = "archive", "Zipping the manifests"
    UPLOAD = "upload", "Saving the zip file to private storage"
    EMAIL = "email", "Emailing the user a download link"
    DONE = "done", "Done"


class DataExport(TimestampedModel):
    """
    A user's data export.

    :param user: The user whose resources are exported, in every account that they belong to.
    :param status: One of :class:`DataExportStatus`.
    :param step: The step that it is on, one of :class:`DataExportStep`.
    :param resource_count: How many resources the user owns.
    :param manifest_count: How many manifests have been written so far.
    :param failed_count: How many resources had no manifest, e.g. because one is broken.
    :param size_bytes: The size of the zip file.
    :param object_key: The zip file's key in private storage, until it is deleted.
    :param expires_at: When the emailed link stops working.
    :param completed_at: When it succeeded or failed.
    :param error: Why it failed, or an empty string.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="data_exports")
    status = models.CharField(max_length=16, choices=DataExportStatus.choices, default=DataExportStatus.QUEUED)
    step = models.CharField(max_length=16, choices=DataExportStep.choices, default=DataExportStep.QUEUED)
    resource_count = models.PositiveIntegerField(default=0)
    manifest_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    size_bytes = models.PositiveBigIntegerField(default=0)
    object_key = models.CharField(max_length=255, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")

    class Meta:
        """Metadata for the model."""

        verbose_name = "Data Export"
        verbose_name_plural = "Data Exports"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user} data export {self.pk} ({self.status})"

    @property
    def is_finished(self) -> bool:
        """Whether it succeeded or failed."""
        finished = (DataExportStatus.SUCCEEDED, DataExportStatus.FAILED)
        return self.status in finished

    @property
    def is_stale(self) -> bool:
        """Whether it was abandoned: unfinished for longer than :data:`DATA_EXPORT_STALE_AFTER`."""
        if self.is_finished:
            return False
        age = timezone.now() - self.created_at
        return age > DATA_EXPORT_STALE_AFTER

    @property
    def is_in_progress(self) -> bool:
        """Whether it is queued or running, and not abandoned."""
        if self.is_finished:
            return False
        return not self.is_stale

    def link_expires_in(self, now: Optional[datetime] = None) -> Optional[timedelta]:
        """
        How long the emailed link still works.

        :param now: The current time. Defaults to ``timezone.now()``.
        :returns: The time left, or None if there is no link, or it has expired.
        """
        if self.expires_at is None:
            return None
        now = now or timezone.now()
        remaining = self.expires_at - now
        if remaining.total_seconds() <= 0:
            return None
        return remaining
