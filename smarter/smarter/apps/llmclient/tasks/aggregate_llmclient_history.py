"""Celery tasks for llmclient app."""

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


def aggregate_llmclient_history():
    """Summarize detail llmclient history into aggregate records."""

    # TODO: implement me.
    logger.info("%s.aggregate_llmclient_history() - Aggregating llmclient history.", logger_prefix)
