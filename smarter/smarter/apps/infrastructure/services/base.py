"""
The base class of every infrastructure service.

:class:`InfrastructureService` gives each service, whichever provider implements it:

- its identity in signals and logs: :attr:`~InfrastructureService.service_name` and
  :attr:`~InfrastructureService.provider_name`.
- the signals of :mod:`smarter.apps.infrastructure.signals`, sent with :meth:`~InfrastructureService.send`,
  and the lifecycle helpers that send them in the right order.
- :meth:`~InfrastructureService.operation`, which translates a provider's SDK errors into the
  service's own exception, so that the platform never catches a provider's exceptions.
- the unit test guard: :func:`refuse_in_unit_tests`.

:class:`DiscoveredResource` describes a resource that a service found, rather than created, for
the inventory, :mod:`smarter.apps.infrastructure.services.inventory`.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from django.dispatch import Signal

from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest import running_unit_tests

from ..exceptions import (
    InfrastructureConfigurationError,
    InfrastructureNotReadyError,
    SmarterInfrastructureError,
)
from ..signals import (
    billable_resource_created,
    billable_resource_creating,
    billable_resource_destroyed,
    billable_resource_destroying,
    infrastructure_connected,
    infrastructure_connection_failed,
    infrastructure_operation_failed,
    resource_created,
    resource_destroyed,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])


def refuse_in_unit_tests(what: str, allow_in_tests: bool = False) -> None:
    """
    Refuse to reach real infrastructure from the unit tests.

    The Smarter containers' cloud credentials and kubeconfig are real, and can create billable
    resources. A real service calls this before it reaches its backend. Tests install a fake,
    e.g. :class:`~smarter.apps.infrastructure.providers.memory.InMemoryProvider` with
    :func:`~smarter.apps.infrastructure.providers.configure_provider`, or pass
    ``allow_in_tests=True`` when they mock the backend themselves, or are tagged
    :data:`~smarter.lib.unittest.runner.INFRASTRUCTURE`.

    :param what: What is refused, for the error message.
    :param allow_in_tests: True to allow it anyway.
    :raises InfrastructureConfigurationError: In the unit tests, unless allowed.
    """
    if running_unit_tests() and not allow_in_tests:
        raise InfrastructureConfigurationError(
            f"Refusing to reach {what} from the unit tests. Install a fake, e.g. with "
            "smarter.apps.infrastructure.providers.configure_provider(), or pass allow_in_tests=True."
        )


@dataclass
class DiscoveredResource:
    """
    A resource that exists in the platform's infrastructure, whoever created it.

    e.g. a Kubernetes node, or the Kubernetes cluster itself.

    :param resource_type: The kind of resource, e.g. ``kubernetes.node``.
    :param resource_name: The resource's name, e.g. ``ip-192-168-1-1.ec2.internal``.
    :param resource_id: The provider's id of the resource, if any, e.g. its ARN.
    :param billable: Whether the provider bills for the resource.
    """

    resource_type: str
    resource_name: str
    resource_id: str = ""
    billable: bool = False


class InfrastructureService(ABC, SmarterHelperMixin):
    """
    The base class of every infrastructure service.

    :param provider_name: The name of the cloud provider that implements the service, e.g. ``aws``.
        Services that do not depend on a cloud, e.g. SMTP email, use their protocol's name.
    """

    service_name: str = "service"
    """The name of the service in signals and logs, see :class:`~smarter.apps.infrastructure.const.InfrastructureServiceNames`."""

    error_class: type[SmarterInfrastructureError] = SmarterInfrastructureError
    """The exception that :meth:`operation` raises for a provider's errors."""

    def __init__(self, provider_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider_name = str(provider_name)
        self._connected: Optional[bool] = None

    def __str__(self) -> str:
        return f"{self.provider_name}.{self.service_name}"

    @property
    @abstractmethod
    def ready(self) -> bool:
        """Whether the service is authenticated and connected, i.e. it can be used."""

    def require_ready(self) -> None:
        """
        Raise unless the service is ready.

        :raises InfrastructureNotReadyError: If the service is not ready.
        """
        if not self.ready:
            raise InfrastructureNotReadyError(f"The {self} infrastructure service is not ready.")

    # --------------------------------------------------------------------------
    # signals
    # --------------------------------------------------------------------------
    def send(self, signal: Signal, **kwargs) -> None:
        """Send one of the infrastructure signals, with this service's ``service`` and ``provider``."""
        signal.send(sender=self.__class__, service=str(self.service_name), provider=self.provider_name, **kwargs)

    def connection_state(self, connected: bool, error: Optional[str] = None) -> bool:
        """
        Record whether the service is connected to its backend.

        Sends :data:`~smarter.apps.infrastructure.signals.infrastructure_connected` or
        :data:`~smarter.apps.infrastructure.signals.infrastructure_connection_failed` when the
        state changes, rather than on every check.

        :param connected: Whether the service is connected.
        :param error: Why it is not connected.
        :returns: ``connected``.
        """
        if connected != self._connected:
            if connected:
                self.send(infrastructure_connected)
            else:
                self.send(infrastructure_connection_failed, error=error or "not connected")
        self._connected = connected
        return connected

    def creating_resource(
        self, resource_type: str, resource_name: str, billable: bool = False, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Send the signal that precedes the creation of a resource.

        Only billable resources have a "creating" signal, so that what costs money can be
        stopped or audited before it exists.

        :returns: The resource's signal arguments, for :meth:`created_resource`.
        """
        resource = {"resource_type": resource_type, "resource_name": resource_name, "billable": billable, **kwargs}
        if billable:
            self.send(billable_resource_creating, resource_type=resource_type, resource_name=resource_name)
        return resource

    def created_resource(self, resource: dict[str, Any], resource_id: Optional[str] = None) -> None:
        """Send the signal that follows the creation of a resource."""
        signal = billable_resource_created if resource["billable"] else resource_created
        self.send(
            signal,
            resource_type=resource["resource_type"],
            resource_name=resource["resource_name"],
            resource_id=resource_id,
        )

    def destroying_resource(
        self, resource_type: str, resource_name: str, resource_id: Optional[str] = None, billable: bool = False
    ) -> dict[str, Any]:
        """
        Send the signal that precedes the destruction of a resource.

        :returns: The resource's signal arguments, for :meth:`destroyed_resource`.
        """
        resource = {
            "resource_type": resource_type,
            "resource_name": resource_name,
            "resource_id": resource_id,
            "billable": billable,
        }
        if billable:
            self.send(
                billable_resource_destroying,
                resource_type=resource_type,
                resource_name=resource_name,
                resource_id=resource_id,
            )
        return resource

    def destroyed_resource(self, resource: dict[str, Any]) -> None:
        """Send the signal that follows the destruction of a resource."""
        signal = billable_resource_destroyed if resource["billable"] else resource_destroyed
        self.send(
            signal,
            resource_type=resource["resource_type"],
            resource_name=resource["resource_name"],
            resource_id=resource["resource_id"],
        )

    # --------------------------------------------------------------------------
    # error handling
    # --------------------------------------------------------------------------
    @contextmanager
    def operation(self, name: str) -> Iterator[None]:
        """
        Run one of the service's operations, translating its errors.

        An infrastructure error passes through. Any other error, e.g. a cloud SDK's, is raised
        as the service's :attr:`error_class`. Either way,
        :data:`~smarter.apps.infrastructure.signals.infrastructure_operation_failed` is sent.

        .. code-block:: python

            with self.operation("create_zone"):
                response = self.client.create_hosted_zone(...)

        :param name: The operation's name, e.g. ``create_zone``.
        """
        try:
            yield
        except SmarterInfrastructureError as e:
            self.send(infrastructure_operation_failed, operation=name, error=str(e))
            raise
        except Exception as e:
            logger.error("%s.%s() failed: %s", self.formatted_class_name, name, e)
            self.send(infrastructure_operation_failed, operation=name, error=str(e))
            raise self.error_class(f"{self} {name} failed: {e}") from e


__all__ = ["DiscoveredResource", "InfrastructureService", "refuse_in_unit_tests"]
