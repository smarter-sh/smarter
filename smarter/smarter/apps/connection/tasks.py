# pylint: disable=unused-argument
"""
Celery tasks for the connection app.
"""

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

# from smarter.workers.celery import app


logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.CONNECTION_LOGGING]
)
module_prefix = "smarter.apps.connection.tasks."
