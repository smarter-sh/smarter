"""
Celery tasks for the vectorstore app.
"""

import logging
import os

from smarter.apps.vectorstore.models import VectorDatabase
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper, current_job_id
from smarter.workers.celery import app


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.TASK_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.VECTORSTORE_LOGGING
    )


base_logger = logging.getLogger(__name__)
base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def embed_and_load_pdf(self) -> bool:
    """
    Celery task to load pdf documents into a vectorstore.
    """
    job_id = self.request.id
    token = current_job_id.set(job_id)

    try:
        db = VectorDatabase.objects.first()
        if not db:
            logger.error(f"{logger_prefix} No vector database found.")
            return False
        service = VectorstoreService(db=db)

        service.pdf_loader("")

        return True
    # pylint: disable=broad-except
    except Exception as e:
        logger.error(f"{logger_prefix} Error occurred: {e}")
        return False
    finally:
        current_job_id.reset(token)
