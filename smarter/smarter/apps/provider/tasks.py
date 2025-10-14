# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from django.conf import settings

from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.workers.celery import app

from .verification import verify_provider as verification_verify_provider
from .verification import verify_provider_model as verification_verify_provider_model


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.TASK_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PROVIDER_LOGGING)
        and level >= smarter_settings.log_level
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
module_prefix = "smarter.apps.provider.tasks."


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def verify_provider_model(provider_model_id):
    """
    Run test bank on provider model.
    """
    verification_verify_provider_model(provider_model_id=provider_model_id)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def verify_provider(provider_id):
    """
    Run test bank on provider.
    """
    verification_verify_provider(provider_id=provider_id)
