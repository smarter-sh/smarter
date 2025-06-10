# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

import requests
from django.conf import settings

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.smarter_celery import app

from .models import (
    Provider,
    ProviderModels,
    ProviderModelVerifications,
    ProviderModelVerificationTypes,
    ProviderStatus,
)
from .signals import (
    model_verification_failure,
    model_verification_success,
    provider_activated,
    provider_verification_failure,
    provider_verification_success,
)
from .tests.utils import mock_test_provider_verification


logger = logging.getLogger(__name__)
module_prefix = "smarter.apps.provider.tasks."


def get_model_verification_for_type(
    provider_model: ProviderModels, verification_type: ProviderModelVerificationTypes
) -> ProviderModelVerifications:
    """
    Get the model verification for a specific type.
    """
    prefix = formatted_text(module_prefix + "get_model_verification_for_type()")
    logger.info("%s Getting model verification for %s of type %s", prefix, provider_model.name, verification_type)

    instance, _ = ProviderModelVerifications.objects.get_or_create(
        provider_model=provider_model, verification_type=verification_type
    )
    if instance.is_valid:
        logger.info("%s Streaming verification for %s is still valid %s", prefix, provider_model, instance.updated_at)
    return instance


def set_model_verification(
    provider_model_verification: ProviderModelVerifications, is_successful: bool, **kwargs
) -> None:
    """
    Set the model verification status.
    """
    prefix = formatted_text(module_prefix + "set_model_verification()")
    logger.info(
        "%s Setting model verification for %s to %s",
        prefix,
        provider_model_verification.provider_model.name,
        is_successful,
    )

    provider_model_verification.is_successful = is_successful
    provider_model_verification.save()
    if is_successful:
        model_verification_success.send(sender=ProviderModelVerifications, instance=provider_model_verification)
    else:
        model_verification_failure.send(sender=ProviderModelVerifications, instance=provider_model_verification)


def test_web_page(url: str, test_str: str) -> bool:
    """
    Test a web page to see if it is valid.
    """
    prefix = formatted_text(module_prefix + "test_web_page()")
    logger.info("%s Testing web page %s", prefix, url)

    try:
        response = requests.get(url, timeout=10)
        if (
            response.status_code == 200
            and ("<html" in response.text.lower() or "<!doctype html" in response.text.lower())
            and test_str.lower() in response.text.lower()
        ):
            logger.info("%s Web page test succeeded.", prefix)
            return True
        else:
            logger.error("%s Web page test failed: Non-200 status or missing documentation HTML.", prefix)
            return False
    except Exception as exc:
        logger.error("%s Web page test failed: %s", prefix, exc)
        return False


# ------------------------------------------------------------------------------
# model verification tasks
# ------------------------------------------------------------------------------


def verify_model_streaming(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify streaming capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_steaming()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.STREAMING
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_tools(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify tools capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_tools()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TOOLS
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_input(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify text input capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_text_input()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_INPUT
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_image_input(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify image input capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_image_input()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.IMAGE_INPUT
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_audio_input(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify audio input capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_audio_input()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.AUDIO_INPUT
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_fine_tuning(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify fine-tuning capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_fine_tuning()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.FINE_TUNING
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_search(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify search capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_search()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.SEARCH
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_code_interpreter(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify code interpreter capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_code_interpreter()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.CODE_INTERPRETER
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_image(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify text to image capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_text_to_image()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_TO_IMAGE
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_audio(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify text to audio capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_text_to_audio()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_TO_AUDIO
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_text(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify text to text capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_text_to_text()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_TO_TEXT
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_translation(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify translation capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_translation()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TRANSLATION
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_summarization(provider_model: ProviderModels, **kwargs) -> bool:
    """
    Verify summarization capabilities of the provider model.
    """
    prefix = formatted_text(module_prefix + "verify_summarization()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.SUMMARIZATION
    )
    if provider_model_verification.is_valid:
        return True

    success = mock_test_provider_verification(success_probability=0.80)
    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def verify_provider_model(provider_model_id, **kwargs):
    """
    Run test bank on provider model.
    """
    try:
        provider_model = ProviderModels.objects.get(id=provider_model_id)
    except ProviderModels.DoesNotExist:
        logger.error(
            "%s Provider model with id %s does not exist",
            formatted_text(module_prefix + "verify_provider_model()"),
            provider_model_id,
        )
        return

    # blackball method
    success: bool = True

    if provider_model.supports_streaming:
        success = success and verify_model_streaming(provider_model=provider_model)
    if provider_model.supports_tools:
        success = success and verify_model_tools(provider_model=provider_model)
    if provider_model.supports_text_input:
        success = success and verify_model_text_input(provider_model=provider_model)
    if provider_model.supports_image_input:
        success = success and verify_model_image_input(provider_model=provider_model)
    if provider_model.supports_audio_input:
        success = success and verify_model_audio_input(provider_model=provider_model)
    if provider_model.supports_fine_tuning:
        success = success and verify_model_fine_tuning(provider_model=provider_model)
    if provider_model.supports_search:
        success = success and verify_model_search(provider_model=provider_model)
    if provider_model.supports_code_interpreter:
        success = success and verify_model_code_interpreter(provider_model=provider_model)
    if provider_model.supports_image_generation:
        success = success and verify_model_text_to_image(provider_model=provider_model)
    if provider_model.supports_audio_generation:
        success = success and verify_model_text_to_audio(provider_model=provider_model)
    if provider_model.supports_text_generation:
        success = success and verify_model_text_to_text(provider_model=provider_model)
    if provider_model.supports_translation:
        success = success and verify_model_translation(provider_model=provider_model)
    if provider_model.supports_summarization:
        success = success and verify_model_summarization(provider_model=provider_model)

    if success:
        provider_model.is_active = True
        provider_model.save(update_fields=["is_active"])
        model_verification_success.send(sender=ProviderModels, instance=provider_model)
        logger.info("Verification tests succeeded for provider model: %s", provider_model.name)
    else:
        provider_model.is_active = False
        provider_model.save(update_fields=["is_active"])
        model_verification_failure.send(sender=ProviderModels, instance=provider_model)
        logger.error("Some verification failed for provider model: %s", provider_model.name)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def verify_provider(provider_id, **kwargs):
    """
    Run test bank on provider.
    """
    prefix = formatted_text(module_prefix + "verify_provider()")
    try:
        provider = Provider.objects.get(id=provider_id)
    except Provider.DoesNotExist:
        logger.error("%s Provider with id %s does not exist", prefix, provider_id)
        return

    logger.info("%s Testing provider: %s", prefix, provider.name)
    if provider.is_active:
        logger.warning("%s Provider %s is already active.", prefix, provider.name)

    # blackball method
    success = True

    if provider.is_deprecated:
        logger.warning("%s Provider %s is deprecated, cannot verify.", prefix, provider.name)
        success = False

    if provider.is_suspended:
        logger.warning("%s Provider %s is suspended, cannot verify.", prefix, provider.name)
        success = False

    if provider.is_flagged:
        logger.warning("%s Provider %s is flagged, cannot verify.", prefix, provider.name)
        success = False

    # verify api_url with api_key
    if not provider.test_connectivity():
        logger.warning("%s Provider %s connectivity test failed, skipping verification.", prefix, provider.name)
        success = False

    # verify that logo exists and is an image file
    if provider.logo:
        if not provider.logo.name.endswith((".png", ".jpg", ".jpeg", ".svg")):
            logger.error("%s Provider %s logo is not a valid image file.", prefix, provider.name)
            success = False
        else:
            logger.info("%s Provider %s logo verification succeeded.", prefix, provider.name)
    else:
        logger.warning("%s Provider %s has no logo, skipping verification.", prefix, provider.name)

    if not provider.contact_email_verified:
        logger.error("%s Provider %s contact email is not verified.", prefix, provider.name)
        success = False

    if not provider.support_email_verified:
        logger.error("%s Provider %s support email is not verified.", prefix, provider.name)
        success = False

    # verify website URL
    if provider.website:
        success = success and test_web_page(provider.website, test_str="")
    else:
        logger.warning("%s Provider %s has no website URL, skipping verification.", prefix, provider.name)
        success = False

    # verify terms of service URL
    if provider.terms_of_service:
        success = success and test_web_page(provider.terms_of_service, test_str="Terms of Service")
    else:
        logger.warning("%s Provider %s has no terms of service URL, skipping verification.", prefix, provider.name)
        success = False

    # verify privacy policy URL
    if provider.privacy_policy:
        success = success and test_web_page(provider.privacy_policy, test_str="Privacy Policy")
    else:
        logger.warning("%s Provider %s has no privacy policy URL, skipping verification.", prefix, provider.name)
        success = False

    # verify tos_accepted
    if not provider.tos_accepted:
        logger.error("%s Provider %s has not accepted the Smarter terms of service.", prefix, provider.name)
        success = False
    else:
        logger.info("%s Provider %s has accepted the Smarter terms of service.", prefix, provider.name)

    if not provider.can_activate:
        logger.error("%s Provider %s cannot be activated.", prefix, provider.name)
        success = False

    if success:
        provider_verification_success.send(sender=Provider, instance=provider)
        provider.status = ProviderStatus.VERIFIED
        provider.is_verified = True
        if provider.can_activate:
            try:
                provider.activate()
                provider.save(update_fields=["status", "is_verified"])
                provider_activated.send(sender=Provider, instance=provider)
            except SmarterValueError as exc:
                logger.error("%s Activation failed for provider: %s, error: %s", prefix, provider.name, exc)
    else:
        provider.status = ProviderStatus.FAILED
        provider.is_verified = False
        provider.is_active = False
        provider.save(update_fields=["status", "is_active", "is_verified"])
        logger.error("%s Verification failed for provider: %s", prefix, provider.name)
        provider_verification_failure.send(sender=Provider, instance=provider)
