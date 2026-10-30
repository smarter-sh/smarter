"""
Annotation handlers: code that reacts when annotations with a given prefix change.

A handler is the Smarter counterpart of a Kubernetes controller that watches an annotation. An
integration owns a key prefix, e.g. ``acme.com``, and registers a handler for it. Whenever a
manifest is applied, or a resource deleted, in a way that adds, changes or removes an annotation
whose prefix is ``acme.com`` or one of its subdomains, the handler is called once per changed
annotation, after the database transaction commits.

**Example:**

.. code-block:: python

    # acme_integration/apps.py
    from django.apps import AppConfig

    class AcmeIntegrationConfig(AppConfig):
        name = "acme_integration"

        def ready(self):
            from . import handlers  # noqa: F401  registers the handlers below

    # acme_integration/handlers.py
    from smarter.lib.annotation.handlers import AnnotationEvent, annotation_handler
    from .tasks import link_crm_account

    @annotation_handler("acme.com")
    def crm_account(event: AnnotationEvent) -> None:
        if event.change.key == "acme.com/crm-account-id" and event.change.action != "removed":
            link_crm_account.delay(event.model_label, event.object_id, event.change.new_value)

Handlers run in the request that applied the manifest. Hand slow work, such as calls to a legacy
system, to a Celery task. An exception in a handler is logged, and doesn't affect the resource or
the other handlers.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Optional, Union

from django.db import models, transaction

from smarter.lib import logging

from .contract import AnnotationChange
from .signals import annotations_changed
from .validation import (
    DNS_SUBDOMAIN_PATTERN,
    SmarterAnnotationError,
    is_reserved_annotation_key,
    prefix_matches,
)

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@dataclass(frozen=True)
class AnnotationEvent:
    """What an annotation handler is called with: one changed annotation of one resource."""

    instance: models.Model
    """The resource.

    After a deletion, it is the deleted instance, and its ``pk`` may be ``None``.
    """

    model_label: str
    """The resource's model, e.g. ``llmclient.LLMClient``."""

    object_id: Union[int, str]
    """The resource's primary key.

    Unlike ``instance.pk``, it survives the resource's deletion.
    """

    change: AnnotationChange
    """The annotation's key, and its value before and after."""

    resource_deleted: bool = False
    """True when the annotation was removed because the resource was deleted."""


AnnotationHandler = Callable[[AnnotationEvent], None]
"""A function that is called with an :class:`AnnotationEvent`."""

_handlers: dict[str, list[AnnotationHandler]] = {}


def register_annotation_handler(prefix: str, handler: AnnotationHandler) -> AnnotationHandler:
    """
    Call ``handler`` whenever an annotation whose key's prefix is ``prefix``, or a subdomain of it, changes.

    The prefixes that belong to the Smarter platform, ``smarter.sh`` and its subdomains, may only
    be handled by Smarter's own code.

    :param prefix: A DNS domain that the integration owns, e.g. ``acme.com``.
    :type prefix: str
    :param handler: The function to call.
    :type handler: AnnotationHandler
    :raises SmarterAnnotationError: If the prefix isn't a DNS subdomain, or is reserved.
    :returns: The handler, so that this can be used as a decorator.
    :rtype: AnnotationHandler
    """
    if not DNS_SUBDOMAIN_PATTERN.match(prefix):
        raise SmarterAnnotationError(f"Annotation handler prefix {prefix!r} must be a lowercase DNS subdomain.")
    module = getattr(handler, "__module__", "") or ""
    if is_reserved_annotation_key(prefix + "/x") and not module.startswith("smarter."):
        raise SmarterAnnotationError(
            f"Annotation prefix {prefix!r} is reserved for the Smarter platform. Use a domain that you own."
        )
    handlers = _handlers.setdefault(prefix, [])
    if handler not in handlers:
        handlers.append(handler)
    logger.debug("%s.register_annotation_handler() %s handles %s", logger_prefix, handler, prefix)
    return handler


def annotation_handler(prefix: str) -> Callable[[AnnotationHandler], AnnotationHandler]:
    """
    Register the decorated function as an annotation handler for ``prefix``.

    See :func:`register_annotation_handler`.

    :param prefix: A DNS domain that the integration owns, e.g. ``acme.com``.
    :type prefix: str
    :returns: The decorator.
    :rtype: Callable[[AnnotationHandler], AnnotationHandler]
    """
    return partial(register_annotation_handler, prefix)


def unregister_annotation_handler(prefix: str, handler: AnnotationHandler) -> None:
    """
    Stop calling ``handler`` for ``prefix``.

    Does nothing if it isn't registered.

    :param prefix: The prefix it was registered for.
    :type prefix: str
    :param handler: The handler.
    :type handler: AnnotationHandler
    """
    handlers = _handlers.get(prefix, [])
    if handler in handlers:
        handlers.remove(handler)
    if not handlers:
        _handlers.pop(prefix, None)


def handlers_for_key(key: str) -> list[AnnotationHandler]:
    """
    Return the handlers to call when the annotation ``key`` changes.

    :param key: An annotation key.
    :type key: str
    :returns: The handlers of every registered prefix that the key's prefix matches.
    :rtype: list[AnnotationHandler]
    """
    key_prefix = key.split("/", 1)[0] if "/" in key else None
    retval: list[AnnotationHandler] = []
    for prefix, handlers in _handlers.items():
        if prefix_matches(key_prefix, prefix):
            retval.extend(handlers)
    return retval


def _send(
    instance: models.Model, object_id: Union[int, str], changes: list[AnnotationChange], resource_deleted: bool
) -> None:
    """Send the signal, then call each handler with each of its changes."""
    # pylint: disable=W0212
    model_label = instance._meta.label  # pylint: disable=W0212
    responses = annotations_changed.send_robust(
        sender=instance.__class__,
        instance=instance,
        object_id=object_id,
        changes=changes,
        resource_deleted=resource_deleted,
    )
    for receiver, response in responses:
        if isinstance(response, Exception):
            logger.error(
                "%s._send() annotations_changed receiver %s failed for %s %s: %s",
                logger_prefix,
                receiver,
                model_label,
                object_id,
                response,
            )
    for change in changes:
        for handler in handlers_for_key(change.key):
            event = AnnotationEvent(
                instance=instance,
                model_label=model_label,
                object_id=object_id,
                change=change,
                resource_deleted=resource_deleted,
            )
            try:
                handler(event)
            # pylint: disable=broad-exception-caught
            except Exception:
                logger.exception(
                    "%s._send() annotation handler %s failed for %s %s, key %s",
                    logger_prefix,
                    handler,
                    model_label,
                    object_id,
                    change.key,
                )


def dispatch_annotation_changes(
    instance: models.Model, changes: list[AnnotationChange], resource_deleted: bool = False
) -> None:
    """
    Send ``changes`` to the ``annotations_changed`` signal and the matching handlers, once the transaction commits.

    :param instance: The resource.
    :type instance: models.Model
    :param changes: What changed.
    :type changes: list[AnnotationChange]
    :param resource_deleted: True when the resource was deleted.
    :type resource_deleted: bool
    """
    if not changes:
        return
    object_id: Optional[Union[int, str]] = instance.pk
    if object_id is None:
        return
    transaction.on_commit(partial(_send, instance, object_id, list(changes), resource_deleted))


__all__ = [
    "AnnotationEvent",
    "AnnotationHandler",
    "annotation_handler",
    "dispatch_annotation_changes",
    "handlers_for_key",
    "register_annotation_handler",
    "unregister_annotation_handler",
]
