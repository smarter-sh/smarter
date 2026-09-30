"""
Celery tasks for the guardrail app.

- :func:`purge_guardrail_events` deletes old guardrail events. Celery Beat runs it daily.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import datetime

from django.db.models import Q
from django.utils import timezone

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from ..models import GuardrailDisposition, GuardrailEvent

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.GUARDRAIL_LOGGING]
)

EVENT_RETENTION_DAYS = 90
"""Days to keep guardrail events."""

AWAITING_REVIEW = (GuardrailDisposition.FLAGGED, GuardrailDisposition.ESCALATED)
"""The dispositions of events that await review, and are kept until they are reviewed."""


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def purge_guardrail_events(days: int = EVENT_RETENTION_DAYS) -> int:
    """
    Delete the guardrail events older than ``days``, except those that await review.

    :param days: The number of days of events to keep.
    :returns: The number of events deleted.
    :rtype: int
    """
    cutoff = timezone.now() - datetime.timedelta(days=days)
    awaiting_review = Q(disposition__in=AWAITING_REVIEW, reviewed=False)
    deleted, _ = GuardrailEvent.objects.filter(created_at__lt=cutoff).exclude(awaiting_review).delete()
    logger.info(
        "%s deleted %s guardrail events older than %s days.",
        formatted_text("smarter.apps.guardrail.tasks.purge_guardrail_events()"),
        deleted,
        days,
    )
    return deleted


__all__ = ["purge_guardrail_events", "EVENT_RETENTION_DAYS"]
