"""Delete the orphaned DNS records of deleted LLMClients."""

from smarter.apps.llmclient.tasks.delete_orphan_dns_records import (
    MAX_DELETIONS_PER_RUN,
    delete_orphan_dns_records,
)
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py delete_orphan_dns_records command."""

    help = (
        "Delete the A records, in the zone of the environment's API domain, of hosts that no LLMClient or LLMHost "
        f"uses, at most {MAX_DELETIONS_PER_RUN} per run. Runs only in the AWS environments. Celery Beat runs this "
        "daily. Use --dry-run to list the orphaned records without deleting them."
    )

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--dry-run", action="store_true", help="List the orphaned records, but delete nothing.")

    def handle(self, *args, **options):
        self.handle_begin()
        dry_run = options["dry_run"]
        names = delete_orphan_dns_records(dry_run=dry_run)
        verb = "Would delete" if dry_run else "Deleted"
        for name in names:
            self.stdout.write(f"{verb} the orphaned A record {name}")
        self.stdout.write(self.style.SUCCESS(f"{verb} {len(names)} orphaned A records."))
        self.handle_completed_success()
