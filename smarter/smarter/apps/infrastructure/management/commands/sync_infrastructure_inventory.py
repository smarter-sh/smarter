"""Discover the platform's Kubernetes cluster, and reconcile the ledger of infrastructure resources with it."""

from smarter.apps.infrastructure.services.inventory import sync_inventory
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py sync_infrastructure_inventory command."""

    help = (
        "Discover the platform's Kubernetes cluster: the cluster, its add-ons, node groups, nodes, volumes, "
        "load balancers, ingresses and certificates, and record them in the ledger of infrastructure resources. "
        "Read-only: nothing is created or destroyed in the cloud."
    )

    def handle(self, *args, **options):
        self.handle_begin()
        try:
            results = sync_inventory()
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc, f"Failed to sync the infrastructure inventory: {exc}")
            raise
        if not results:
            self.stdout.write(self.style.WARNING("Nothing could be listed. Is the Kubernetes cluster available?"))
        for resource_type, counts in sorted(results.items()):
            self.stdout.write(
                f"{resource_type}: {counts['found']} found, {counts['created']} created, "
                f"{counts['destroyed']} destroyed"
            )
        self.handle_completed_success()
