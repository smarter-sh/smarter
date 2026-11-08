"""Point the ingresses of deployed LLMClients at the api's renamed Kubernetes Service."""

from smarter.apps.llmclient.tasks.retarget_ingresses import retarget_llmclient_ingresses
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py retarget_llmclient_ingresses command."""

    help = (
        "Rewrite the ingress of each deployed LLMClient host that still sends its requests to the api's old "
        "Kubernetes Service, smarter, so that it names smarter-api. initialize_platform runs this. Use --dry-run "
        "to list the ingresses without changing them."
    )

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--dry-run", action="store_true", help="List the ingresses, but change nothing.")

    def handle(self, *args, **options):
        """
        Rewrite, or with ``--dry-run`` list, the ingresses, and print each one's host and the total.

        :param args: Positional arguments (unused).
        :param options: The parsed options; ``dry_run`` lists the ingresses without changing them.
        """
        self.handle_begin()
        dry_run = options["dry_run"]
        hosts = retarget_llmclient_ingresses(dry_run=dry_run)
        verb = "Would retarget" if dry_run else "Retargeted"
        for host in hosts:
            self.stdout.write(f"{verb} the ingress of {host}")
        self.stdout.write(self.style.SUCCESS(f"{verb} {len(hosts)} LLMClient ingresses."))
        self.handle_completed_success()
