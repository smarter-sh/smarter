"""Celery tasks for llm_client app."""

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


def aggregate_llm_client_history():
    """Summarize detail llm_client history into aggregate records."""

    # TODO: implement me.
    logger.info("%s.aggregate_llm_client_history() - Aggregating llm_client history.", logger_prefix)
