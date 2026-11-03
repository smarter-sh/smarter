"""
Celery tasks for the doodle app.

- :func:`plan_doodles` plans the doodles of every region a week ahead, and deletes the old ones.
  Celery Beat runs it daily.
"""

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from . import planner
from .const import PLANNING_DAYS

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.DOODLE_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def plan_doodles(days: int = PLANNING_DAYS) -> int:
    """
    Plan the doodles of every region, ``days`` days ahead.

    :param days: How many days ahead to plan.
    :returns: The number of doodles planned.
    :rtype: int
    """
    logger.info("%s.plan_doodles() planning the doodles %s days ahead.", logger_prefix, days)
    planned = planner.plan_doodles(days=days)
    return planned


__all__ = ["plan_doodles"]
