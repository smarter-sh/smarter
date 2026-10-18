"""Discover the platform's Kubernetes cluster, and reconcile the ledger of infrastructure resources with it."""

from smarter.apps.infrastructure.services.inventory import (
    KUBERNETES_SOURCES,
    sync_inventory,
)
from smarter.common.conf import smarter_settings
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py sync_infrastructure_inventory command."""

    help = (
        "Discover the platform's Kubernetes cluster: the cluster, its add-ons, node groups, nodes, volumes, "
        "load balancers, ingresses and certificates, and record them in the ledger of infrastructure resources. "
        "Read-only: nothing is created or destroyed in the cloud."
    )

    def summary(self, resource_type: str, counts: dict[str, int]) -> str:
        """
        Describe one resource type's reconciliation.

        The inventory creates and destroys nothing: ``created`` counts resources that it found and
        recorded in the ledger for the first time, e.g. a node that the autoscaler added, and
        ``destroyed`` counts those that it found gone. Namespaced types name the namespace,
        because resources of other namespaces, e.g. a shared ingress controller's load
        balancer, are not counted.

        :param resource_type: The resource type, e.g. ``kubernetes.node``.
        :param counts: The counts that :func:`sync_inventory` returned for the type.
        :returns: One line of output.
        """
        namespaced = {source.resource_type for source in KUBERNETES_SOURCES if source.namespaced}
        scope = f" in namespace {smarter_settings.environment_namespace}" if resource_type in namespaced else ""
        return (
            f"{resource_type}: {counts['found']} found{scope}, {counts['created']} newly recorded, "
            f"{counts['destroyed']} no longer found"
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
            self.stdout.write(self.summary(resource_type, counts))
        self.handle_completed_success()
