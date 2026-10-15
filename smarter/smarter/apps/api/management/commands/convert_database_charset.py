# pylint: disable=W0613
"""
Convert the database, and every table that is not utf8mb4, to the utf8mb4 character set.

Older deployments created their tables as utf8mb3, which rejects emoji and other 4-byte
characters. The Helm chart's init Job runs this after ``migrate``. It is idempotent.
"""

from smarter.lib.django.database import convert_database_to_utf8mb4
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py convert_database_charset command."""

    help = "Convert the database, and every table that is not utf8mb4, to utf8mb4."

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--database", default="default", help="The Django database alias.")
        parser.add_argument("--dry-run", action="store_true", help="List the tables, without converting them.")

    def handle(self, *args, **options):
        """Convert the tables that are not utf8mb4."""
        self.handle_begin()
        try:
            tables = convert_database_to_utf8mb4(using=options["database"], dry_run=options["dry_run"])
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc, "Failed to convert the database to utf8mb4.")
            raise
        verb = "Would convert" if options["dry_run"] else "Converted"
        self.stdout.write(f"{verb} {len(tables)} tables to utf8mb4: {', '.join(tables) or 'none'}.")
        self.handle_completed_success()
