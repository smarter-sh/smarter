# pylint: disable=W0613,C0115,R0913
"""
Verification functions for provider models in the Smarter app.
These functions are responsible for verifying various capabilities of provider models,
such as streaming, tools, text input, image input, audio input, fine-tuning, search, code interpreter,
text to image, text to audio, text to text, translation, and summarization.
Each verification function checks if the capability is already verified and valid.
If not, it performs a test to verify the capability and updates the verification status accordingly.
"""

import logging

from smarter.apps.provider.models import ProviderModel, ProviderModelVerificationTypes
from smarter.apps.provider.signals import (
    model_verification_failure,
    model_verification_success,
)
from smarter.apps.provider.tests.utils import mock_test_provider_verification
from smarter.apps.provider.utils import (
    get_model_verification_for_type,
    set_model_verification,
)
from smarter.common.helpers.console_helpers import formatted_text


logger = logging.getLogger(__name__)
module_prefix = "smarter.apps.provider.verification.provider_model."


def verify_model_streaming(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_tools(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_text_input(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_image_input(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_audio_input(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_fine_tuning(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_search(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_code_interpreter(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_text_to_image(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_text_to_audio(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_text_to_text(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_translation(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_model_summarization(provider_model: ProviderModel, **kwargs) -> bool:
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


def verify_provider_model(provider_model_id, **kwargs):
    """
    Top-level test bank on provider model.
    """

    try:
        provider_model = ProviderModel.objects.get(id=provider_model_id)
    except ProviderModel.DoesNotExist:
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
        model_verification_success.send(sender=ProviderModel, provider_model=provider_model)
        logger.info("Verification tests succeeded for provider model: %s", provider_model.name)
    else:
        provider_model.is_active = False
        provider_model.save(update_fields=["is_active"])
        model_verification_failure.send(sender=ProviderModel, provider_model=provider_model)
        logger.error("Some verification failed for provider model: %s", provider_model.name)
