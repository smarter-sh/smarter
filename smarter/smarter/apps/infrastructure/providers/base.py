"""
The base class of the cloud providers.

A cloud provider implements the services that depend on a cloud, :class:`CloudProvider.dns` and
:class:`CloudProvider.certificates`, and contributes what the cloud-independent services need
from it: the Kubernetes cluster's kubeconfig, and the cluster's description.

To add a cloud, e.g. Azure:

1. Add a package, ``smarter.apps.infrastructure.providers.azure``, with a :class:`CloudProvider`
   whose DNS and certificate services implement the primitives of
   :class:`~smarter.apps.infrastructure.services.dns.DNSService` and
   :class:`~smarter.apps.infrastructure.services.certificates.CertificateService`.
2. Register it, in :mod:`smarter.apps.infrastructure.providers`, under its
   :class:`~smarter.apps.infrastructure.const.CloudProviders` name.
3. Set ``SMARTER_CLOUD_PROVIDER=azure``.

The platform does not change.
"""

from abc import abstractmethod
from typing import Any, Optional

from ..const import InfrastructureServiceNames
from ..services.base import InfrastructureService
from ..services.certificates import CertificateService
from ..services.dns import DNSService
from ..signals import infrastructure_authenticated, infrastructure_authentication_failed


class CloudProvider(InfrastructureService):
    """
    A cloud provider: the cloud-specific half of the infrastructure services.

    :param allow_in_tests: Allow the provider to reach its cloud in the unit tests, e.g. in a
        test tagged :data:`~smarter.lib.unittest.runner.INFRASTRUCTURE`.
    """

    name: str = "cloud"
    """The provider's name, see :class:`~smarter.apps.infrastructure.const.CloudProviders`."""

    service_name = InfrastructureServiceNames.PROVIDER

    def __init__(self, allow_in_tests: bool = False, **kwargs):
        super().__init__(provider_name=self.name, **kwargs)
        self.allow_in_tests = allow_in_tests
        self._authenticated: Optional[bool] = None

    def authentication_state(self, identity: Optional[dict], error: Optional[str] = None) -> bool:
        """
        Record whether the provider is authenticated with its cloud.

        Sends :data:`~smarter.apps.infrastructure.signals.infrastructure_authenticated` or
        :data:`~smarter.apps.infrastructure.signals.infrastructure_authentication_failed` when the
        state changes, rather than on every check.

        :param identity: The provider's identity, or None if it is not authenticated.
        :param error: Why it is not authenticated.
        :returns: Whether it is authenticated.
        """
        authenticated = isinstance(identity, dict)
        if authenticated != self._authenticated:
            if authenticated:
                self.send(infrastructure_authenticated, identity=identity)
            else:
                self.send(infrastructure_authentication_failed, error=error or "not authenticated")
        self._authenticated = authenticated
        return authenticated

    @property
    @abstractmethod
    def identity(self) -> Optional[dict[str, Any]]:
        """The identity that the provider authenticates as, e.g. its account, or None."""

    @property
    def account_id(self) -> Optional[str]:
        """The cloud account's id, or None if the provider is not authenticated."""
        return None

    @property
    @abstractmethod
    def sdk_version(self) -> str:
        """The version of the provider's SDK."""

    @property
    @abstractmethod
    def dns(self) -> DNSService:
        """The provider's DNS service."""

    @property
    @abstractmethod
    def certificates(self) -> CertificateService:
        """The provider's TLS certificate service."""

    @abstractmethod
    def update_kubeconfig(self) -> bool:
        """
        Write the kubeconfig of the platform's Kubernetes cluster, for kubectl.

        :returns: True if it was written.
        """

    def get_kubernetes_token(self) -> Optional[tuple[str, float]]:
        """
        Return a bearer token for the platform's Kubernetes cluster, which kubectl uses instead of its kubeconfig's.

        The kubeconfig of a managed cluster usually runs a command to fetch a token, e.g. ``aws eks
        get-token``, on every kubectl call, which takes seconds. A provider that can create a token
        itself returns one, which is used until it expires.

        :returns: The token and when it expires, as a :func:`time.time`, or None for kubectl to use
            its kubeconfig's credentials.
        """
        return None

    @abstractmethod
    def get_kubernetes_cluster_info(self) -> dict[str, Any]:
        """
        Describe the platform's Kubernetes cluster, e.g. for the status API.

        :raises InfrastructureNotReadyError: If the provider is not ready.
        """


__all__ = ["CloudProvider"]
