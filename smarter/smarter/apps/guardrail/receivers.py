"""
Django Signal Receivers for guardrail.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Guardrail
from .serializers import GuardrailSerializer
from .signals import (
    guardrail_blocked,
    guardrail_escalated,
    guardrail_failed,
    guardrail_triggered,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

module_prefix = __name__


@receiver(post_save, sender=Guardrail)
def guardrail_saved(sender, instance: Guardrail, created: bool, **kwargs):
    """Log a created or updated Guardrail."""
    prefix = logging.formatted_text(f"{module_prefix}.guardrail_saved()")
    data = logging.formatted_json(GuardrailSerializer(instance).data)
    logger.info("%s - %s %s, %s", prefix, "created" if created else "updated", instance, data)


@receiver(pre_delete, sender=Guardrail)
def guardrail_deleted(sender, instance: Guardrail, **kwargs):
    """Log a deleted Guardrail."""
    prefix = logging.formatted_text(f"{module_prefix}.guardrail_deleted()")
    logger.info("%s - %s", prefix, instance)


@receiver(guardrail_triggered, dispatch_uid="guardrail_triggered")
def handle_guardrail_triggered(sender, guardrail: Guardrail, stage: str, disposition: str, **kwargs):
    """Log a triggered guardrail.

    What it matched is not logged, because it may be personal data.
    """
    logger.info(
        "%s - %s %s: %s",
        logging.formatted_text(f"{module_prefix}.guardrail_triggered"),
        guardrail.name,
        stage,
        disposition,
    )


@receiver(guardrail_blocked, dispatch_uid="guardrail_blocked")
def handle_guardrail_blocked(sender, guardrail: Guardrail, stage: str, message: str, **kwargs):
    """Log a blocked message or reply."""
    logger.warning(
        "%s - %s blocked the %s: %s",
        logging.formatted_text(f"{module_prefix}.guardrail_blocked"),
        guardrail.name,
        stage,
        message,
    )


@receiver(guardrail_escalated, dispatch_uid="guardrail_escalated")
def handle_guardrail_escalated(sender, guardrail: Guardrail, stage: str, event=None, **kwargs):
    """Log an escalation to human review.

    Its event awaits review in the Smarter admin.
    """
    logger.warning(
        "%s - %s escalated the %s to human review, severity %s, event %s",
        logging.formatted_text(f"{module_prefix}.guardrail_escalated"),
        guardrail.name,
        stage,
        guardrail.severity,
        event.pk if event else None,
    )


@receiver(guardrail_failed, dispatch_uid="guardrail_failed")
def handle_guardrail_failed(sender, guardrail: Guardrail, stage: str, error: str, fail_closed: bool, **kwargs):
    """Log a guardrail that failed to run."""
    logger.error(
        "%s - %s failed on the %s%s: %s",
        logging.formatted_text(f"{module_prefix}.guardrail_failed"),
        guardrail.name,
        stage,
        ", and blocked it" if fail_closed else "",
        error,
    )
