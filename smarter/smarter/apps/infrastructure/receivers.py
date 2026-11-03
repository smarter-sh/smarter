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

from typing import Optional

from django.dispatch import receiver

from smarter.apps.infrastructure.services.email import masked_recipients
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
    return f"{logging.SmarterFormattedText.text(module_prefix)}.{fn_name}()" + f" [{provider}.{service}]"


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
    """
    Log that a provider authenticated with its cloud.

    Only the last four characters of the cloud account id are logged. The id isn't a secret, but job
    logs are emailed and shipped elsewhere, and the full id isn't needed to tell accounts apart.
    """
    identity = identity or {}
    account = identity.get("Account")
    if not account:
        account = identity.get("account")
    logger.info("%s authenticated, account %s", _prefix("authenticated", service, provider), _mask_account(account))


def _mask_account(account) -> Optional[str]:
    """
    Mask a cloud account id, all but its last four characters.

    :param account: the account id, e.g. an AWS account number, or None.
    :returns: e.g. ``********3456``, the id unchanged when it has four characters or fewer, or None.
    """
    if not account:
        return None
    account = str(account)
    if len(account) <= 4:
        return account
    return "*" * (len(account) - 4) + account[-4:]


@receiver(infrastructure_authentication_failed, dispatch_uid="infrastructure_authentication_failed")
def handle_infrastructure_authentication_failed(sender, service, provider, error=None, **kwargs):
    """
    Log that a provider could not authenticate with its cloud.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param error: Why it failed.
    :param kwargs: The signal's other arguments.
    """
    logger.error("%s authentication failed: %s", _prefix("authentication_failed", service, provider), error)


@receiver(infrastructure_connected, dispatch_uid="infrastructure_connected")
def handle_infrastructure_connected(sender, service, provider, **kwargs):
    """
    Log that a service connected to its backend.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param kwargs: The signal's other arguments.
    """
    logger.info("%s connected", _prefix("connected", service, provider))


@receiver(infrastructure_connection_failed, dispatch_uid="infrastructure_connection_failed")
def handle_infrastructure_connection_failed(sender, service, provider, error=None, **kwargs):
    """
    Log that a service could not connect to its backend.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param error: Why it failed.
    :param kwargs: The signal's other arguments.
    """
    logger.error("%s connection failed: %s", _prefix("connection_failed", service, provider), error)


@receiver(billable_resource_creating, dispatch_uid="infrastructure_billable_resource_creating")
def handle_billable_resource_creating(sender, service, provider, resource_type, resource_name, **kwargs):
    """
    Log that a billable resource is about to be created.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param resource_type: The resource's type, e.g. ``dns.zone``.
    :param resource_name: The resource's name, e.g. ``example.com``.
    :param kwargs: The signal's other arguments.
    """
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
    """
    Log that a billable resource was created, and record it in the ledger.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param resource_type: The resource's type, e.g. ``dns.zone``.
    :param resource_name: The resource's name, e.g. ``example.com``.
    :param resource_id: The resource's cloud id, or None if the provider has not assigned one.
    :param kwargs: The signal's other arguments. ``reconciled`` is True when the inventory found the resource, or
        found it gone, rather than a service creating or destroying it.
    """
    if kwargs.get("reconciled"):
        # the inventory found it, or found it gone: no service created it.
        logger.info(
            "%s found billable %s %s (%s), which already exists, and recorded it in the ledger",
            _prefix("billable_resource_created", service, provider),
            resource_type,
            resource_name,
            resource_id,
        )
    else:
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
    """
    Log that a billable resource is about to be destroyed.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param resource_type: The resource's type, e.g. ``dns.zone``.
    :param resource_name: The resource's name, e.g. ``example.com``.
    :param resource_id: The resource's cloud id, or None if the provider has not assigned one.
    :param kwargs: The signal's other arguments.
    """
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
    """
    Log that a billable resource was destroyed, and record it in the ledger.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param resource_type: The resource's type, e.g. ``dns.zone``.
    :param resource_name: The resource's name, e.g. ``example.com``.
    :param resource_id: The resource's cloud id, or None if the provider has not assigned one.
    :param kwargs: The signal's other arguments. ``reconciled`` is True when the inventory found the resource, or
        found it gone, rather than a service creating or destroying it.
    """
    if kwargs.get("reconciled"):
        # the inventory found it, or found it gone: no service destroyed it.
        logger.info(
            "%s found that billable %s %s (%s) no longer exists, and recorded it in the ledger",
            _prefix("billable_resource_destroyed", service, provider),
            resource_type,
            resource_name,
            resource_id,
        )
    else:
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
    """
    Log that a resource was created or updated, and record it in the ledger.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param resource_type: The resource's type, e.g. ``dns.zone``.
    :param resource_name: The resource's name, e.g. ``example.com``.
    :param resource_id: The resource's cloud id, or None if the provider has not assigned one.
    :param kwargs: The signal's other arguments. ``reconciled`` is True when the inventory found the resource, or
        found it gone, rather than a service creating or destroying it.
    """
    if kwargs.get("reconciled"):
        # the inventory found it, or found it gone: no service created it.
        logger.info(
            "%s found %s %s (%s), which already exists, and recorded it in the ledger",
            _prefix("resource_created", service, provider),
            resource_type,
            resource_name,
            resource_id,
        )
    else:
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
    """
    Log that a resource was destroyed, and record it in the ledger.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param resource_type: The resource's type, e.g. ``dns.zone``.
    :param resource_name: The resource's name, e.g. ``example.com``.
    :param resource_id: The resource's cloud id, or None if the provider has not assigned one.
    :param kwargs: The signal's other arguments. ``reconciled`` is True when the inventory found the resource, or
        found it gone, rather than a service creating or destroying it.
    """
    if kwargs.get("reconciled"):
        # the inventory found it, or found it gone: no service destroyed it.
        logger.info(
            "%s found that %s %s (%s) no longer exists, and recorded it in the ledger",
            _prefix("resource_destroyed", service, provider),
            resource_type,
            resource_name,
            resource_id,
        )
    else:
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
    """
    Log that Kubernetes resources were applied.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param kinds: The kinds of the manifest's resources, or None.
    :param kwargs: The signal's other arguments.
    """
    logger.info("%s applied %s", _prefix("resource_applied", service, provider), ", ".join(kinds or []))


@receiver(infrastructure_operation_failed, dispatch_uid="infrastructure_operation_failed")
def handle_infrastructure_operation_failed(sender, service, provider, operation=None, error=None, **kwargs):
    """
    Log that a service's operation failed.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param operation: The operation that failed, e.g. ``apply_manifest``.
    :param error: Why it failed.
    :param kwargs: The signal's other arguments.
    """
    logger.error("%s %s failed: %s", _prefix("operation_failed", service, provider), operation, error)


@receiver(email_sent, dispatch_uid="infrastructure_email_sent")
def handle_email_sent(sender, service, provider, subject=None, recipients=None, **kwargs):
    """
    Log that an email was sent. The recipients are logged masked, e.g. ``j****@example.com``.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param subject: The email's subject.
    :param recipients: The email's recipients.
    :param kwargs: The signal's other arguments.
    """
    logged_recipients = masked_recipients(recipients)
    logger.info("%s sent '%s' to %s", _prefix("email_sent", service, provider), subject, logged_recipients)


@receiver(email_failed, dispatch_uid="infrastructure_email_failed")
def handle_email_failed(sender, service, provider, subject=None, recipients=None, error=None, **kwargs):
    """
    Log that an email could not be sent. The recipients are logged masked, e.g. ``j****@example.com``.

    :param sender: The service's class.
    :param service: The service's name, e.g. ``dns``.
    :param provider: The cloud provider's name, e.g. ``aws``.
    :param subject: The email's subject.
    :param recipients: The email's recipients.
    :param error: Why it failed.
    :param kwargs: The signal's other arguments.
    """
    logged_recipients = masked_recipients(recipients)
    logger.error(
        "%s could not send '%s' to %s: %s",
        _prefix("email_failed", service, provider),
        subject,
        logged_recipients,
        error,
    )
