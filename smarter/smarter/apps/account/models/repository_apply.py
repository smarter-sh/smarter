"""
A batch apply of a GitHub repository's manifests, which a user starts from the web console's Apply page.

The Celery task :func:`smarter.apps.account.tasks.apply_repository` clones the repository, records each
manifest that it finds as a :class:`RepositoryApplyManifest`, pending, then applies them one by one, as
``manage.py load_from_github`` does, and records each one's result: applied, skipped or failed, with why.
The web console polls the run, and shows each manifest's state. See :mod:`smarter.apps.account.repository_apply`.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from smarter.lib.django.models import TimestampedModel

from .user_profile import UserProfile

REPOSITORY_APPLY_STALE_AFTER = timedelta(minutes=30)
"""A run that has neither finished nor failed after this long is abandoned, e.g. its worker restarted.

The user may then start another.
"""


class RepositoryApplyStatus(models.TextChoices):
    """Where a batch apply is in its life."""

    QUEUED = "queued", "Waiting for a worker"
    CLONING = "cloning", "Cloning the repository"
    APPLYING = "applying", "Applying the manifests"
    FINISHED = "finished", "Finished: each manifest was applied, skipped or failed"
    FAILED = "failed", "Failed as a whole, e.g. the repository couldn't be cloned"


class RepositoryApplyManifestStatus(models.TextChoices):
    """What became of one manifest of a batch apply."""

    PENDING = "pending", "Pending"
    APPLIED = "applied", "Applied"
    SKIPPED = "skipped", "Skipped"
    FAILED = "failed", "Failed"


class RepositoryApply(TimestampedModel):
    """
    A batch apply of a GitHub repository's manifests.

    :param user_profile: The user who started it, as whom every manifest is applied, in their account.
    :param url: The repository, e.g. ``https://github.com/smarter-sh/example-manifests``.
    :param commit: The commit that was cloned, or an empty string before then, or if git couldn't tell.
    :param status: One of :class:`RepositoryApplyStatus`.
    :param error: Why the run failed as a whole, e.g. the repository couldn't be cloned. A manifest's
        own failure is its :attr:`RepositoryApplyManifest.message`.
    :param completed_at: When it finished or failed.
    """

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="repository_applies")
    url = models.URLField(max_length=255)
    commit = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=16, choices=RepositoryApplyStatus, default=RepositoryApplyStatus.QUEUED)
    error = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Metadata for the model."""

        verbose_name = "Repository Apply"
        verbose_name_plural = "Repository Applies"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.url} ({self.status})"

    @property
    def is_finished(self) -> bool:
        """Whether it finished or failed."""
        finished = (RepositoryApplyStatus.FINISHED, RepositoryApplyStatus.FAILED)
        return self.status in finished

    @property
    def is_stale(self) -> bool:
        """Whether it was abandoned: unfinished for longer than :data:`REPOSITORY_APPLY_STALE_AFTER`."""
        if self.is_finished:
            return False
        if self.created_at is None:
            # not saved yet.
            return False
        age = timezone.now() - self.created_at
        return age > REPOSITORY_APPLY_STALE_AFTER

    @property
    def is_in_progress(self) -> bool:
        """Whether it is queued, cloning or applying, and not abandoned."""
        if self.is_finished:
            return False
        return not self.is_stale


class RepositoryApplyManifest(TimestampedModel):
    """
    One manifest of a batch apply, in the order in which it is applied.

    :param repository_apply: The run.
    :param position: Its place in the order of application, from 0.
    :param path: Its file, relative to the repository's root, e.g. ``plugins/sql/stackademy-sql.yaml``.
    :param kind: Its kind, e.g. ``SqlPlugin``.
    :param name: Its ``metadata.name``.
    :param status: One of :class:`RepositoryApplyManifestStatus`.
    :param message: Why it failed or was skipped, or an empty string.
    :param output: What applying it printed, for a user who investigates a failure.
    """

    repository_apply = models.ForeignKey(RepositoryApply, on_delete=models.CASCADE, related_name="manifests")
    position = models.PositiveIntegerField()
    path = models.CharField(max_length=1024)
    kind = models.CharField(max_length=64)
    name = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=16, choices=RepositoryApplyManifestStatus, default=RepositoryApplyManifestStatus.PENDING
    )
    message = models.TextField(blank=True, default="")
    output = models.TextField(blank=True, default="")

    class Meta:
        """Metadata for the model."""

        verbose_name = "Repository Apply Manifest"
        verbose_name_plural = "Repository Apply Manifests"
        ordering = ("repository_apply", "position")
        constraints = [
            models.UniqueConstraint(
                fields=["repository_apply", "position"], name="account_repositoryapplymanifest_unique_position"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.path} ({self.status})"


__all__ = [
    "REPOSITORY_APPLY_STALE_AFTER",
    "RepositoryApply",
    "RepositoryApplyManifest",
    "RepositoryApplyManifestStatus",
    "RepositoryApplyStatus",
]
