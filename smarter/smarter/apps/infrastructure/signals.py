"""
Signals of the infrastructure app.

They are sent by the infrastructure services, :mod:`smarter.apps.infrastructure.services`,
whichever cloud provider implements them, so that the platform can observe its infrastructure,
e.g. to audit or meter the billable resources that it creates, without knowing which cloud it
runs on. The sender is the service's class.

Every signal has the arguments ``service``, the name of the service, e.g. ``dns`` (see
:class:`~smarter.apps.infrastructure.const.InfrastructureServiceNames`), and ``provider``,
the name of the cloud provider, e.g. ``aws``, plus those listed.

Resource signals also have ``resource_type``, e.g. ``dns.zone``, and ``resource_name``,
e.g. ``example.com``, and ``resource_id`` once the provider has assigned one.

Example::

    from django.dispatch import receiver
    from smarter.apps.infrastructure.signals import billable_resource_created

    @receiver(billable_resource_created)
    def meter(sender, service, provider, resource_type, resource_name, resource_id, **kwargs):
        ...
"""

from django.dispatch import Signal

infrastructure_authenticated = Signal()
"""Sent when a provider authenticates with its cloud, the first time and after a failure.

Arguments: service, provider, identity (dict), the provider's account identity, e.g. its
account id.
"""

infrastructure_authentication_failed = Signal()
"""Sent when a provider cannot authenticate with its cloud, the first time and after a success.

Arguments: service, provider, error (str).
"""

infrastructure_connected = Signal()
"""Sent when a service connects to its backend, e.g. a Kubernetes cluster, or a cloud API.

Arguments: service, provider.
"""

infrastructure_connection_failed = Signal()
"""Sent when a service cannot connect to its backend.

Arguments: service, provider, error (str).
"""

billable_resource_creating = Signal()
"""Sent before a service creates a resource that its provider bills for, e.g. a DNS zone.

Arguments: service, provider, resource_type, resource_name.
"""

billable_resource_created = Signal()
"""Sent after a service creates a resource that its provider bills for.

Arguments: service, provider, resource_type, resource_name, resource_id.
"""

billable_resource_destroying = Signal()
"""Sent before a service destroys a resource that its provider bills for.

Arguments: service, provider, resource_type, resource_name, resource_id.
"""

billable_resource_destroyed = Signal()
"""Sent after a service destroys a resource that its provider bills for.

Arguments: service, provider, resource_type, resource_name, resource_id.
"""

resource_created = Signal()
"""Sent after a service creates, or updates, a resource that is not billed for on its own.

e.g. a DNS record, or a TLS certificate.

Arguments: service, provider, resource_type, resource_name, resource_id.
"""

resource_destroyed = Signal()
"""Sent after a service destroys a resource that is not billed for on its own.

Arguments: service, provider, resource_type, resource_name, resource_id.
"""

resource_applied = Signal()
"""Sent after Kubernetes resources are created or updated, from a manifest.

Arguments: service, provider, kinds (list[str]), the kinds of the manifest's resources.
"""

infrastructure_operation_failed = Signal()
"""Sent when a service's operation fails.

Arguments: service, provider, operation (str), e.g. ``apply_manifest``, error (str).
"""

email_sent = Signal()
"""Sent after an email is sent.

Arguments: service, provider, subject (str), recipients (list[str]).
"""

email_failed = Signal()
"""Sent when an email cannot be sent.

Arguments: service, provider, subject (str), recipients (list[str]), error (str).
"""

__all__ = [
    "billable_resource_created",
    "billable_resource_creating",
    "billable_resource_destroyed",
    "billable_resource_destroying",
    "email_failed",
    "email_sent",
    "infrastructure_authenticated",
    "infrastructure_authentication_failed",
    "infrastructure_connected",
    "infrastructure_connection_failed",
    "infrastructure_operation_failed",
    "resource_applied",
    "resource_created",
    "resource_destroyed",
]
