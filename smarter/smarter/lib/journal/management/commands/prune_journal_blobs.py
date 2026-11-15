"""Delete the Smarter Journal's blobs that no entry references."""

from datetime import timedelta

from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.journal.models import BLOB_PRUNE_GRACE, SAMJournalBlob


class Command(SmarterCommand):
    """
    Django manage.py prune_journal_blobs command.

    Deletes the :class:`~smarter.lib.journal.models.SAMJournalBlob` rows that no journal entry
    references, and that weren't used for ``--grace-days``, with
    :meth:`~smarter.lib.journal.models.SAMJournalBlobManager.prune`. Celery Beat runs the same, weekly,
    as :func:`smarter.lib.journal.tasks.prune_journal_blobs`. It reads the whole journal.
    """

    help = "Delete the Smarter Journal's blobs that no entry references."

    def add_arguments(self, parser):
        """
        Add the ``--grace-days`` and ``--dry-run`` options.

        :param parser: The command's argument parser.
        """
        parser.add_argument(
            "--grace-days",
            type=int,
            default=BLOB_PRUNE_GRACE.days,
            help="Keep an unreferenced blob for this many days after its last use. More than 1.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Count the blobs, and delete none.")

    def handle(self, *args, **options):
        """
        Prune the blobs, and print how many were deleted.

        :param args: Unused.
        :param options: The command's options, ``grace_days`` and ``dry_run``.
        """
        self.handle_begin()
        grace = timedelta(days=options["grace_days"])
        dry_run = options["dry_run"]
        try:
            count = SAMJournalBlob.objects.prune(grace=grace, dry_run=dry_run)
        except ValueError as e:
            # e.g. --grace-days 1: exits with status 1.
            self.handle_completed_failure(err=e)
            return
        if dry_run:
            self.handle_completed_success(msg=f"{count} unreferenced journal blobs would be deleted.")
        else:
            self.handle_completed_success(msg=f"Deleted {count} unreferenced journal blobs.")
