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


BILLABLE_KUBERNETES_KINDS = ("persistentvolumeclaim",)
"""
Kubernetes kinds that provision a billable cloud resource of their own, e.g. a block storage volume.

A Service of type LoadBalancer, which provisions a cloud load balancer, and a StatefulSet with
volumeClaimTemplates, which provisions volumes, are billable too. See
:func:`smarter.apps.infrastructure.services.kubernetes.billable_resources`.
"""

DEFAULT_DNS_RECORD_TTL = 600
"""Seconds."""
