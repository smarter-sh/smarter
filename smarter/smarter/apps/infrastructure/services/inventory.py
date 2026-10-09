"""
The inventory: what exists in the platform's infrastructure, whoever created it.

The ledger, :class:`~smarter.apps.infrastructure.models.InfrastructureResource`, records what the
services create and destroy, as they do it. Much of the platform's infrastructure is not created
that way: the Kubernetes cluster, its add-ons and node groups are provisioned outside the
platform, e.g. with Terraform, nodes come and go with the cluster's autoscaler, and cert-manager
issues certificates. :func:`sync_inventory` discovers them, see :class:`InventorySource`, and
reconciles the ledger. Besides the cluster itself, i.e. the cluster, its add-ons, node groups
and nodes, it discovers only the environment's resources, those of
``smarter_settings.environment_namespace``, because the cluster is shared by every environment:

- a resource that the ledger does not know is recorded as created,
- an active resource that no longer exists is recorded as destroyed,

with the resource signals of :mod:`smarter.apps.infrastructure.signals`, so that the ledger is
still written only by their receivers. A resource type that cannot be listed, e.g. because the
cluster is unavailable, is left as it is, rather than recorded as destroyed.

The Celery Beat task :func:`smarter.apps.infrastructure.tasks.sync_infrastructure_inventory`
runs it every few minutes, and ``manage.py sync_infrastructure_inventory`` on demand.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..const import KubernetesResourceTypes
from ..models import InfrastructureResource
from . import infrastructure
from .base import DiscoveredResource
from .kubernetes import KubernetesService

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])
logger_prefix = logging.formatted_text(__name__)


def _name(item: dict) -> str:
    return str((item.get("metadata") or {}).get("name", ""))


def _load_balancer_hostname(item: dict) -> str:
    """The cloud load balancer's hostname, or IP address, of an Ingress or a Service."""
    ingress = ((item.get("status") or {}).get("loadBalancer") or {}).get("ingress") or [{}]
    return str(ingress[0].get("hostname") or ingress[0].get("ip") or "")


def _volume_id(item: dict) -> str:
    """The cloud volume's id of a PersistentVolume, e.g. an EBS volume id."""
    spec = item.get("spec") or {}
    return str(
        (spec.get("csi") or {}).get("volumeHandle") or (spec.get("awsElasticBlockStore") or {}).get("volumeID") or ""
    )


def _claimed_by_environment(item: dict) -> bool:
    """Whether a PersistentVolume is bound to a claim in the environment's namespace."""
    claim = (item.get("spec") or {}).get("claimRef") or {}
    return claim.get("namespace") == smarter_settings.environment_namespace


@dataclass
class InventorySource:
    """
    A kind of Kubernetes resource that the inventory lists, and how it is recorded.

    Only the environment's resources are recorded, i.e. those of
    ``smarter_settings.environment_namespace``: the cluster is shared by every environment.

    :param resource_type: The ledger's resource type.
    :param kind: The Kubernetes kind, e.g. ``node``.
    :param namespaced: Whether to list the environment's namespace, rather than the cluster.
        Resources are named as the Kubernetes service records them, e.g. when it deletes an
        Ingress, so that the two agree.
    :param billable: Whether the cloud bills for the resource.
    :param resource_id: The resource's cloud id.
    :param include: Whether a resource is recorded, e.g. only Services of type LoadBalancer, or
        only the PersistentVolumes of the environment's claims.
    """

    resource_type: str
    kind: str
    namespaced: bool
    billable: bool
    resource_id: Callable[[dict], str]
    include: Callable[[dict], bool] = lambda item: True

    def find(self, kubernetes: KubernetesService) -> Optional[list[DiscoveredResource]]:
        """The resources of this source that exist, or None if they could not be listed."""
        namespace = smarter_settings.environment_namespace if self.namespaced else None
        items = kubernetes.find_resources(self.kind, namespace)
        if items is None:
            return None
        return [
            DiscoveredResource(self.resource_type, _name(item), self.resource_id(item), self.billable)
            for item in items
            if _name(item) and self.include(item)
        ]


KUBERNETES_SOURCES: list[InventorySource] = [
    InventorySource(
        str(KubernetesResourceTypes.NODE),
        "node",
        namespaced=False,
        billable=True,
        resource_id=lambda item: str((item.get("spec") or {}).get("providerID", "")),
    ),
    InventorySource(
        str(KubernetesResourceTypes.PERSISTENT_VOLUME),
        "persistentvolume",
        namespaced=False,
        billable=True,
        resource_id=_volume_id,
        include=_claimed_by_environment,
    ),
    InventorySource(
        str(KubernetesResourceTypes.LOAD_BALANCER),
        "service",
        namespaced=True,
        billable=True,
        resource_id=_load_balancer_hostname,
        include=lambda item: (item.get("spec") or {}).get("type") == "LoadBalancer",
    ),
    InventorySource(
        str(KubernetesResourceTypes.INGRESS),
        "ingress",
        namespaced=True,
        billable=False,
        resource_id=_load_balancer_hostname,
    ),
    InventorySource(
        str(KubernetesResourceTypes.CERTIFICATE),
        "certificate",
        namespaced=True,
        billable=False,
        resource_id=lambda item: str((item.get("spec") or {}).get("secretName", "")),
    ),
]
"""The Kubernetes resources that the inventory lists."""


def discover() -> dict[str, list[DiscoveredResource]]:
    """
    Discover the platform's Kubernetes cluster: its cloud resources, and its own.

    :returns: The resources, by resource type. A type that could not be listed is left out.
    """
    retval: dict[str, list[DiscoveredResource]] = {}
    try:
        retval.update(infrastructure.provider.get_kubernetes_cluster_resources())
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("%s.discover() could not list the cluster's cloud resources: %s", logger_prefix, e)
    kubernetes = infrastructure.kubernetes
    for source in KUBERNETES_SOURCES:
        try:
            resources = source.find(kubernetes)
        # pylint: disable=broad-except
        except Exception as e:
            logger.warning("%s.discover() could not list %s: %s", logger_prefix, source.resource_type, e)
            continue
        if resources is not None:
            retval[source.resource_type] = resources
    return retval


def reconcile(service: KubernetesService, resource_type: str, resources: list[DiscoveredResource]) -> dict[str, int]:
    """
    Reconcile the ledger's active resources of a type with those that exist.

    :param service: The service that sends the resource signals, whose provider names the
        ledger's resources.
    :param resource_type: The resource type, e.g. ``kubernetes.node``.
    :param resources: The resources of the type that exist.
    :returns: The number of resources that exist, and of those recorded as created and destroyed.
    """
    found = {resource.resource_name: resource for resource in resources}
    active = {
        row.resource_name: row
        for row in InfrastructureResource.objects.filter(
            provider=service.provider_name, resource_type=resource_type, status=InfrastructureResource.Status.ACTIVE
        )
    }
    created = destroyed = 0
    for name, resource in found.items():
        row = active.get(name)
        if row is None:
            signal_args = {"resource_type": resource_type, "resource_name": name, "billable": resource.billable}
            service.created_resource(signal_args, resource_id=resource.resource_id or None)
            created += 1
        elif resource.resource_id and row.resource_id != resource.resource_id:
            # e.g. an Ingress that the service recorded by name, which now has its load balancer.
            row.resource_id = resource.resource_id
            row.save(update_fields=["resource_id", "updated_at"])
    for name, row in active.items():
        if name not in found:
            service.destroyed_resource(service.destroying_resource(resource_type, name, row.resource_id, row.billable))
            destroyed += 1
    return {"found": len(found), "created": created, "destroyed": destroyed}


def sync_inventory() -> dict[str, dict[str, int]]:
    """
    Discover the platform's Kubernetes cluster, and reconcile the ledger with it.

    :returns: For each resource type that could be listed, the number of resources that exist,
        and of those recorded as created and destroyed.
    """
    kubernetes = infrastructure.kubernetes
    retval = {
        resource_type: reconcile(kubernetes, resource_type, resources)
        for resource_type, resources in discover().items()
    }
    logger.info("%s.sync_inventory() %s", logger_prefix, retval)
    return retval


__all__ = ["KUBERNETES_SOURCES", "InventorySource", "discover", "reconcile", "sync_inventory"]
