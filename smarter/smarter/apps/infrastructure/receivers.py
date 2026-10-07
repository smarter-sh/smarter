"""
Django Signal Receivers for the infrastructure app.

They log the infrastructure services' signals, so that every change to the platform's
infrastructure is traceable, whichever cloud provider made it. Billable resources are logged
at warning level, because they cost money, and failures at error level.

The resources that are created and destroyed are also recorded in the ledger,
:class:`~smarter.apps.infrastructure.models.InfrastructureResource`. A ledger that cannot be
written is logged, and never fails the infrastructure operation.
"""

# pylint: disable=W0613

from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import InfrastructureResource
from .signals import (
    billable_resource_created,
    billable_resource_creating,
    billable_resource_destroyed,
    billable_resource_destroying,
    email_failed,
    email_sent,
    infrastructure_authenticated,
    infrastructure_authentication_failed,
    infrastructure_connected,
    infrastructure_connection_failed,
    infrastructure_operation_failed,
    resource_applied,
    resource_created,
    resource_destroyed,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

module_prefix = __name__


def _prefix(fn_name: str, service, provider) -> str:
    return logging.formatted_text(f"{module_prefix}.{fn_name}()") + f" [{provider}.{service}]"


# pylint: disable=too-many-arguments
def _record(created: bool, service, provider, resource_type, resource_name, resource_id, billable: bool) -> None:
    """Record a resource in the ledger."""
    record = InfrastructureResource.record_created if created else InfrastructureResource.record_destroyed
    try:
        record(
            provider=str(provider),
            service=str(service),
            resource_type=str(resource_type),
            resource_name=str(resource_name),
            resource_id=str(resource_id) if resource_id else None,
            billable=billable,
        )
    # pylint: disable=broad-except
    except Exception as e:
        logger.error(
            "%s could not record %s %s: %s", _prefix("record", service, provider), resource_type, resource_name, e
        )


@receiver(infrastructure_authenticated, dispatch_uid="infrastructure_authenticated")
def handle_infrastructure_authenticated(sender, service, provider, identity=None, **kwargs):
    """Log that a provider authenticated with its cloud."""
    account = (identity or {}).get("Account") or (identity or {}).get("account")
    logger.info("%s authenticated, account %s", _prefix("authenticated", service, provider), account)


@receiver(infrastructure_authentication_failed, dispatch_uid="infrastructure_authentication_failed")
def handle_infrastructure_authentication_failed(sender, service, provider, error=None, **kwargs):
    """Log that a provider could not authenticate with its cloud."""
    logger.error("%s authentication failed: %s", _prefix("authentication_failed", service, provider), error)


@receiver(infrastructure_connected, dispatch_uid="infrastructure_connected")
def handle_infrastructure_connected(sender, service, provider, **kwargs):
    """Log that a service connected to its backend."""
    logger.info("%s connected", _prefix("connected", service, provider))


@receiver(infrastructure_connection_failed, dispatch_uid="infrastructure_connection_failed")
def handle_infrastructure_connection_failed(sender, service, provider, error=None, **kwargs):
    """Log that a service could not connect to its backend."""
    logger.error("%s connection failed: %s", _prefix("connection_failed", service, provider), error)


@receiver(billable_resource_creating, dispatch_uid="infrastructure_billable_resource_creating")
def handle_billable_resource_creating(sender, service, provider, resource_type, resource_name, **kwargs):
    """Log that a billable resource is about to be created."""
    logger.warning(
        "%s creating billable %s %s",
        _prefix("billable_resource_creating", service, provider),
        resource_type,
        resource_name,
    )


@receiver(billable_resource_created, dispatch_uid="infrastructure_billable_resource_created")
def handle_billable_resource_created(
    sender, service, provider, resource_type, resource_name, resource_id=None, **kwargs
):
    """Log that a billable resource was created, and record it in the ledger."""
    logger.warning(
        "%s created billable %s %s (%s)",
        _prefix("billable_resource_created", service, provider),
        resource_type,
        resource_name,
        resource_id,
    )
    _record(True, service, provider, resource_type, resource_name, resource_id, billable=True)


@receiver(billable_resource_destroying, dispatch_uid="infrastructure_billable_resource_destroying")
def handle_billable_resource_destroying(
    sender, service, provider, resource_type, resource_name, resource_id=None, **kwargs
):
    """Log that a billable resource is about to be destroyed."""
    logger.warning(
        "%s destroying billable %s %s (%s)",
        _prefix("billable_resource_destroying", service, provider),
        resource_type,
        resource_name,
        resource_id,
    )


@receiver(billable_resource_destroyed, dispatch_uid="infrastructure_billable_resource_destroyed")
def handle_billable_resource_destroyed(
    sender, service, provider, resource_type, resource_name, resource_id=None, **kwargs
):
    """Log that a billable resource was destroyed, and record it in the ledger."""
    logger.warning(
        "%s destroyed billable %s %s (%s)",
        _prefix("billable_resource_destroyed", service, provider),
        resource_type,
        resource_name,
        resource_id,
    )
    _record(False, service, provider, resource_type, resource_name, resource_id, billable=True)


@receiver(resource_created, dispatch_uid="infrastructure_resource_created")
def handle_resource_created(sender, service, provider, resource_type, resource_name, resource_id=None, **kwargs):
    """Log that a resource was created or updated, and record it in the ledger."""
    logger.info(
        "%s created %s %s (%s)",
        _prefix("resource_created", service, provider),
        resource_type,
        resource_name,
        resource_id,
    )
    _record(True, service, provider, resource_type, resource_name, resource_id, billable=False)


@receiver(resource_destroyed, dispatch_uid="infrastructure_resource_destroyed")
def handle_resource_destroyed(sender, service, provider, resource_type, resource_name, resource_id=None, **kwargs):
    """Log that a resource was destroyed, and record it in the ledger."""
    logger.info(
        "%s destroyed %s %s (%s)",
        _prefix("resource_destroyed", service, provider),
        resource_type,
        resource_name,
        resource_id,
    )
    _record(False, service, provider, resource_type, resource_name, resource_id, billable=False)


@receiver(resource_applied, dispatch_uid="infrastructure_resource_applied")
def handle_resource_applied(sender, service, provider, kinds=None, **kwargs):
    """Log that Kubernetes resources were applied."""
    logger.info("%s applied %s", _prefix("resource_applied", service, provider), ", ".join(kinds or []))


@receiver(infrastructure_operation_failed, dispatch_uid="infrastructure_operation_failed")
def handle_infrastructure_operation_failed(sender, service, provider, operation=None, error=None, **kwargs):
    """Log that a service's operation failed."""
    logger.error("%s %s failed: %s", _prefix("operation_failed", service, provider), operation, error)


@receiver(email_sent, dispatch_uid="infrastructure_email_sent")
def handle_email_sent(sender, service, provider, subject=None, recipients=None, **kwargs):
    """Log that an email was sent."""
    logger.info("%s sent '%s' to %s", _prefix("email_sent", service, provider), subject, recipients)


@receiver(email_failed, dispatch_uid="infrastructure_email_failed")
def handle_email_failed(sender, service, provider, subject=None, recipients=None, error=None, **kwargs):
    """Log that an email could not be sent."""
    logger.error(
        "%s could not send '%s' to %s: %s", _prefix("email_failed", service, provider), subject, recipients, error
    )
