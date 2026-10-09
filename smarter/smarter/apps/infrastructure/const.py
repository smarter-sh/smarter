"""Constants for the infrastructure app."""

import os

from smarter.common.enum import SmarterEnumAbstract

namespace = "infrastructure"
presentation_app_name = "Infrastructure"

HERE = os.path.abspath(os.path.dirname(__file__))


class CloudProviders(str, SmarterEnumAbstract):
    """
    The cloud providers that Smarter's infrastructure services can run on.

    ``smarter_settings.cloud_provider`` selects one. Only AWS is implemented: the others are
    reserved, so that a new provider is a new package in
    :mod:`smarter.apps.infrastructure.providers`, registered with
    :func:`~smarter.apps.infrastructure.providers.register_provider`, rather than a change
    to the platform.
    """

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    DIGITALOCEAN = "digitalocean"
    MEMORY = "memory"
    """An in-memory provider, for tests and local development without a cloud account."""


class InfrastructureServiceNames(str, SmarterEnumAbstract):
    """The names of the infrastructure services, as they appear in signals and logs."""

    PROVIDER = "provider"
    DNS = "dns"
    CERTIFICATES = "certificates"
    KUBERNETES = "kubernetes"
    EMAIL = "email"


class CertificateStatus(str, SmarterEnumAbstract):
    """
    The status of a TLS certificate, in any provider's certificate service.

    The names are those of AWS Certificate Manager, which other providers map to.
    """

    PENDING_VALIDATION = "PENDING_VALIDATION"
    ISSUED = "ISSUED"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"
    VALIDATION_TIMED_OUT = "VALIDATION_TIMED_OUT"
    REVOKED = "REVOKED"
    FAILED = "FAILED"


class KubernetesResourceTypes(str, SmarterEnumAbstract):
    """
    The resource types of the Kubernetes cluster that the inventory discovers.

    See :mod:`smarter.apps.infrastructure.services.inventory`. The cluster, its add-ons and its
    node groups are the cloud provider's, and the others are the cluster's own. Besides the
    cluster, its add-ons, node groups and nodes, only the resources of the environment's
    namespace, ``smarter_settings.environment_namespace``, are discovered.
    """

    CLUSTER = "kubernetes.cluster"
    """The managed Kubernetes cluster, e.g. AWS EKS, which is billed by the hour."""
    ADDON = "kubernetes.addon"
    """A managed add-on of the cluster, e.g. the VPC CNI, CoreDNS, or the EBS CSI driver."""
    NODEGROUP = "kubernetes.nodegroup"
    """A managed group of identical nodes.

    Its nodes are billed, not the group.
    """
    NODE = "kubernetes.node"
    """A compute node, e.g. an EC2 instance."""
    PERSISTENT_VOLUME = "kubernetes.persistentvolume"
    """A block storage volume, e.g. an EBS volume, bound to a claim in the environment's namespace."""
    LOAD_BALANCER = "kubernetes.loadbalancer"
    """A Service of type LoadBalancer of the environment's namespace, which provisions a cloud load balancer."""
    INGRESS = "kubernetes.ingress"
    """An Ingress of the environment's namespace."""
    CERTIFICATE = "kubernetes.certificate"
    """A cert-manager Certificate, i.e. an ssl/tls certificate, of the environment's namespace."""


BILLABLE_KUBERNETES_KINDS = ("persistentvolumeclaim",)
"""
Kubernetes kinds that provision a billable cloud resource of their own, e.g. a block storage volume.

A Service of type LoadBalancer, which provisions a cloud load balancer, and a StatefulSet with
volumeClaimTemplates, which provisions volumes, are billable too. See
:func:`smarter.apps.infrastructure.services.kubernetes.billable_resources`.
"""

DEFAULT_DNS_RECORD_TTL = 600
"""Seconds."""
