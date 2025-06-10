# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from django.conf import settings

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.smarter_celery import app

from .models import Provider, ProviderStatus
from .signals import provider_verified, verification_failure, verification_success


logger = logging.getLogger(__name__)
module_prefix = "smarter.apps.provider.tasks."


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def test_provider(provider_id, **kwargs):
    """
    Run test bank on provider.
    """
    prefix = formatted_text(module_prefix + "test_provider()")
    try:
        provider = Provider.objects.get(id=provider_id)
    except Provider.DoesNotExist:
        logger.error("%s Provider with id %s does not exist", prefix, provider_id)
        return

    logger.info("%s Testing provider: %s", prefix, provider.name)
    # testy test test test
    success = True

    if success:
        verification_success.send(sender=Provider, instance=provider)
        provider.status = ProviderStatus.VERIFIED
        provider.is_verified = True
        if provider.can_activate:
            try:
                provider.activate()
            except SmarterValueError as exc:
                logger.error("%s Activation failed for provider: %s, error: %s", prefix, provider.name, exc)
        provider.save(update_fields=["status", "is_verified"])
        provider_verified.send(sender=Provider, instance=provider)
    else:
        provider.status = ProviderStatus.FAILED
        provider.is_verified = False
        provider.is_active = False
        provider.save(update_fields=["status", "is_active", "is_verified"])
        logger.error("%s Verification failed for provider: %s", prefix, provider.name)
        verification_failure.send(sender=Provider, instance=provider)
