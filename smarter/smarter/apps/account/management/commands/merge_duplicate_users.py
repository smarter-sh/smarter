"""
Merge the users that share an email address into one.

Migration ``account.0011_merge_duplicate_users`` does this once on every platform, before
``account.0012_unique_user_email`` makes the address unique. Run this command with ``--dry-run``
first, to see what the migration will merge, rename and delete. Without it, it merges, which is
only needed on a database that is still behind 0012. See :mod:`smarter.apps.account.user_merge`.
"""

from smarter.apps.account.user_merge import historical_apps, merge_duplicate_users
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py merge_duplicate_users command.

    Prints one line per email address that more than one user has, then each row that is renamed.
    With ``--verbose``, also each row that is moved or deleted. Running it again merges nothing.
    """

    help = "Merge the users that share an email address into the one who signed in most recently."

    def add_arguments(self, parser):
        """Add the arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be merged, renamed and deleted, without changing anything.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Also list every row that is moved or deleted.",
        )

    def handle(self, *args, **options):
        """Merge the duplicate users, or report what a merge would do."""
        self.handle_begin()
        dry_run: bool = options.get("dry_run", False)
        verbose: bool = options.get("verbose", False)

        apps = historical_apps()
        reports = merge_duplicate_users(apps, dry_run=dry_run)
        for report in reports:
            self.stdout.write(report.summary())
            for line in report.renamed:
                self.stdout.write(self.style.WARNING(f"  renamed {line}"))
            if not verbose:
                continue
            for line in report.moved:
                self.stdout.write(f"  moved {line}")
            for line in report.deleted:
                self.stdout.write(f"  deleted {line}")

        if dry_run:
            verb = "would be merged"
        else:
            verb = "were merged"
        self.stdout.write(self.style.SUCCESS(f"{len(reports)} email addresses had more than one user, and {verb}."))
        self.handle_completed_success()
