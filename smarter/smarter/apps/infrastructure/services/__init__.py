"""
The infrastructure service layer: the platform's only way to reach its infrastructure.

:data:`infrastructure` gives the platform each service, whichever cloud provider implements it:

.. code-block:: python

    from smarter.apps.infrastructure.services import infrastructure

    zone, created = infrastructure.dns.get_or_create_zone("example.com")
    certificate_id, _ = infrastructure.certificates.get_or_create_certificate("example.com")
    infrastructure.kubernetes.apply_manifest(manifest)
    infrastructure.email.send_email(subject="Hello", body="...", to="user@example.com")

- ``dns``: :class:`~.dns.DNSService`, implemented by the cloud provider, e.g. AWS Route53.
- ``certificates``: :class:`~.certificates.CertificateService`, implemented by the cloud
  provider, e.g. AWS Certificate Manager.
- ``kubernetes``: :class:`~.kubernetes.KubernetesService`, implemented with kubectl, and the
  cloud provider's kubeconfig.
- ``email``: :class:`~.email.EmailService`, implemented with SMTP.
- ``provider``: the :class:`~smarter.apps.infrastructure.providers.base.CloudProvider` of
  ``smarter_settings.cloud_provider``.

Each service is resolved when it is used, not when this module is imported, so that tests can
replace it, with :func:`~smarter.apps.infrastructure.providers.configure_provider`,
:func:`~.kubernetes.configure_kubernetes` and :func:`~.email.configure_email`, and so that
importing the platform never reaches the network.

Tests of code that uses :data:`infrastructure` can also patch it where it is used, e.g.
``patch("smarter.apps.llmclient.tasks.verify_custom_domain.infrastructure")``.
"""

from typing import TYPE_CHECKING

from .base import InfrastructureService, refuse_in_unit_tests
from .certificates import Certificate, CertificateService
from .dns import DNSRecord, DNSService, DNSZone
from .email import (
    EmailService,
    InMemoryEmailService,
    SMTPEmailService,
    configure_email,
    get_email,
)
from .kubernetes import (
    KubectlKubernetesService,
    KubernetesService,
    configure_kubernetes,
    get_kubernetes,
)

if TYPE_CHECKING:
    from ..providers.base import CloudProvider


class InfrastructureServices:
    """The platform's infrastructure services.

    Use the :data:`infrastructure` instance.
    """

    @property
    def provider(self) -> "CloudProvider":
        """The cloud provider, ``smarter_settings.cloud_provider``, unless one is configured."""
        # pylint: disable=import-outside-toplevel
        from ..providers import get_provider

        return get_provider()

    @property
    def ready(self) -> bool:
        """Whether the cloud provider is authenticated."""
        return self.provider.ready

    @property
    def dns(self) -> DNSService:
        """The cloud provider's DNS."""
        return self.provider.dns

    @property
    def certificates(self) -> CertificateService:
        """The cloud provider's TLS certificates."""
        return self.provider.certificates

    @property
    def kubernetes(self) -> KubernetesService:
        """The platform's Kubernetes cluster."""
        return get_kubernetes()

    @property
    def email(self) -> EmailService:
        """The platform's outgoing email."""
        return get_email()


infrastructure = InfrastructureServices()
"""The platform's infrastructure services."""


__all__ = [
    "Certificate",
    "CertificateService",
    "DNSRecord",
    "DNSService",
    "DNSZone",
    "EmailService",
    "InMemoryEmailService",
    "InfrastructureService",
    "InfrastructureServices",
    "KubectlKubernetesService",
    "KubernetesService",
    "SMTPEmailService",
    "configure_email",
    "configure_kubernetes",
    "get_email",
    "get_kubernetes",
    "infrastructure",
    "refuse_in_unit_tests",
]
