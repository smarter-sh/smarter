"""
Celery tasks for the doodle app.

- :func:`plan_doodles` plans the doodles of every region a week ahead, from the calendar, asks the
  Smarter Doodle Editor about each new day (:mod:`smarter.apps.doodle.editor`), and deletes the old
  ones. Celery Beat runs it every six hours.
"""

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from . import editor, planner
from .const import PLANNING_DAYS

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.DOODLE_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def plan_doodles(days: int = PLANNING_DAYS) -> int:
    """
    Plan the doodles of every region, ``days`` days ahead, and let the editor choose those of new days.

    :param days: How many days ahead to plan.
    :returns: The number of doodles planned.
    :rtype: int
    """
    logger.info("%s.plan_doodles() planning the doodles %s days ahead.", logger_prefix, days)
    planned = planner.plan_doodles(days=days)
    window = planner.planning_window(days=days)
    edited = editor.edit_days(window)
    logger.info("%s.plan_doodles() the Smarter Doodle Editor chose the doodles of %s days.", logger_prefix, edited)
    return planned


__all__ = ["plan_doodles"]
