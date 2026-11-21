"""Celery tasks for llmclient app."""

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)


def aggregate_llmclient_history():
    """Summarize detail llmclient history into aggregate records."""

    # TODO: implement me.
    logger.info("Aggregating llmclient history.")
