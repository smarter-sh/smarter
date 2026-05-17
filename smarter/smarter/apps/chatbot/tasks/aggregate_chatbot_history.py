"""
Celery tasks for chatbot app.
"""

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.CHATBOT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


def aggregate_chatbot_history():
    """summarize detail chatbot history into aggregate records."""

    # TODO: implement me.
    logger.info("%s.aggregate_chatbot_history() - Aggregating chatbot history.", logger_prefix)
