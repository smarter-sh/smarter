# pylint: disable=W0613,C0115,R0913,W0718
"""
Verification functions for provider models in the Smarter app.

These functions are responsible for verifying various capabilities of provider models,
such as streaming, tools, text input, image input, audio input, fine-tuning, search, code interpreter,
text to image, text to audio, text to text, translation, and summarization.
Each verification function checks if the capability is already verified and valid.
If not, it performs a test to verify the capability and updates the verification status accordingly.
"""

import io
import wave

import openai
from openai import APIConnectionError, APIStatusError

from smarter.apps.provider.models import ProviderModel, ProviderModelVerificationTypes
from smarter.apps.provider.signals import (
    model_verification_failure,
    model_verification_success,
)
from smarter.apps.provider.utils import (
    get_model_verification_for_type,
    set_model_verification,
)
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROVIDER_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.PLUGIN_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

module_prefix = "smarter.apps.provider.verification.provider_model."

VERIFICATION_MAX_COMPLETION_TOKENS = 1024
"""
The completion budget of the checks that read the model's answer.

Reasoning models spend their budget on reasoning tokens first, and return no text at all when it
runs out, so a budget of a few tokens fails them.
"""

INCONCLUSIVE_STATUS_CODES = (401, 402, 408, 429)
"""Provider http status codes, besides 5xx, that describe the account or the provider rather than the model."""

BILLING_ERROR_MARKERS = ("credit balance", "billing", "insufficient_quota", "exceeded your current quota")
"""Text of a provider error that blames the account's credit or quota, whatever its status code."""


class ProviderModelVerificationInconclusive(Exception):
    """
    Raised by a check when its provider's error says nothing about the model.

    An invalid api key, an account without credit, a rate limit, a provider outage or a network error
    makes every model of the provider fail, working or not. :func:`verify_provider_model` catches it,
    and leaves the model's verifications and its ``is_active`` as they were.
    """


def raise_if_inconclusive(error: Exception) -> None:
    """
    Raise :class:`ProviderModelVerificationInconclusive` if ``error`` is about the account or the provider, not the model.

    Anthropic, for example, reports an account without credit as a 400 ``invalid_request_error``,
    so the error's text is checked as well as its status code.

    :param error: The exception that a check's call to the provider raised.
    :raises ProviderModelVerificationInconclusive: if the error does not show that the model fails the check.
    """
    if isinstance(error, APIConnectionError):
        raise ProviderModelVerificationInconclusive(str(error)) from error
    if isinstance(error, APIStatusError):
        message = str(error).lower()
        if (
            error.status_code in INCONCLUSIVE_STATUS_CODES
            or error.status_code >= 500
            or any(marker in message for marker in BILLING_ERROR_MARKERS)
        ):
            raise ProviderModelVerificationInconclusive(str(error)) from error


def completion_text(response) -> str:
    """
    Return the stripped text of a chat completion's first choice.

    :param response: A chat completion.
    :returns: The text, or an empty string when the message has none, as when a reasoning model runs out of tokens.
    """
    return (response.choices[0].message.content or "").strip()


def verify_model_streaming(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify streaming capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_steaming()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.STREAMING
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.base_url = provider_model.provider.base_url
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        response = openai.chat.completions.create(
            model=provider_model.name,
            messages=[{"role": "user", "content": "Hello"}],
            stream=True,
            max_completion_tokens=10,
        )
        # Try to get the first chunk from the stream
        first_chunk = next(iter(response), None)
        success = first_chunk is not None
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error("Error during verify_model_streaming() for provider model %s", provider_model.name, exc_info=True)
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_tools(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify tools capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_tools()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TOOLS
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.base_url = provider_model.provider.base_url
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.chat.completions.create(
            model=provider_model.name,
            messages=[{"role": "user", "content": "What is the weather in Boston?"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the weather in a given city",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"],
                        },
                    },
                }
            ],
            max_completion_tokens=10,
        )
        success = True
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error("Error during verify_model_tools() for provider model %s", provider_model.name, exc_info=True)
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_input(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify text input capabilities of the provider model."""
    prefix = SmarterFormattedText.text(module_prefix + "verify_text_input()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_INPUT
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.base_url = provider_model.provider.base_url
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.chat.completions.create(
            model=provider_model.name,
            messages=[{"role": "user", "content": "Hello"}],
            max_completion_tokens=5,
        )
        success = True
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error("Error during verify_model_text_input() for provider model %s", provider_model.name, exc_info=True)
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_image_input(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify image input capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_image_input()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.IMAGE_INPUT
    )
    if provider_model_verification.is_valid:
        return True

    try:
        # Example: using a small PNG image as base64 (replace with a real image in production)
        dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgQnQn1wAAAAASUVORK5CYII="
        openai.base_url = provider_model.provider.base_url
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.chat.completions.create(
            model=provider_model.name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{dummy_image_b64}"},
                        },
                    ],
                }
            ],
            max_completion_tokens=5,
        )
        success = True
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error(
            "Error during verify_model_image_input() for provider model %s", provider_model.name, exc_info=True
        )
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_audio_input(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify audio input capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_audio_input()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.AUDIO_INPUT
    )
    if provider_model_verification.is_valid:
        return True

    try:
        # Generate a 1-second silent WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 16000)
        buffer.seek(0)

        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.base_url = provider_model.provider.base_url

        # Try transcription (you can also try translation if needed)
        openai.audio.transcriptions.create(model="gpt-4o-transcribe", file=buffer)

        success = True
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error(
            "Error during verify_model_audio_input() for provider model %s", provider_model.name, exc_info=True
        )
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_fine_tuning(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify fine-tuning capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_fine_tuning()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.FINE_TUNING
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.base_url = provider_model.provider.base_url

        # Attempt to create a fine-tuning job with minimal dummy data
        # This will likely fail due to missing training file, but if the model is unsupported,
        # OpenAI will return a specific error about model support.
        openai.fine_tuning.jobs.create(
            model=provider_model.name, training_file="file-xxxxxxxxxxxxxxxxxxxxxxx"  # Dummy file ID
        )
        success = True
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error(
            "Error during verify_model_fine_tuning() for provider model %s", provider_model.name, exc_info=True
        )
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_search(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify search capabilities of the provider model.

    DEPRECATED: OpenAI has deprecated the search endpoint.
    """
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_search()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.SEARCH
    )

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_code_interpreter(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify code interpreter capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_code_interpreter()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.CODE_INTERPRETER
    )
    if provider_model_verification.is_valid:
        return True

    # List of known models that support code interpreter as of June-2025
    code_interpreter_models = [
        "gpt-4o",
        "gpt-4-turbo",
    ]

    success = provider_model.name in code_interpreter_models

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    if not success:
        logger.error(
            "Provider model %s does not support code interpreter. Known supported models: %s",
            provider_model.name,
            code_interpreter_models,
        )
    return success


def verify_model_text_to_image(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify text to image capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_text_to_image()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_TO_IMAGE
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.base_url = provider_model.provider.base_url

        # Attempt to generate an image with a simple prompt
        openai.images.generate(model=provider_model.name, prompt="A red apple on a table", n=1, size="256x256")
        success = True
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error(
            "Error during verify_model_text_to_image() for provider model %s", provider_model.name, exc_info=True
        )
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_audio(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify text to audio capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_text_to_audio()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_TO_AUDIO
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.base_url = provider_model.provider.base_url

        # Attempt to generate audio from text
        openai.audio.speech.create(
            model=provider_model.name, input="Hello, this is a test.", voice="alloy"  # Use a default voice
        )
        success = True
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error(
            "Error during verify_model_text_to_audio() for provider model %s", provider_model.name, exc_info=True
        )
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_text(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify text to text capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_text_to_text()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_TO_TEXT
    )
    if provider_model_verification.is_valid:
        return True

    success = verify_model_text_input(provider_model=provider_model)

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    if not success:
        logger.error(
            "Provider model %s does not support text to text. Ensure it supports text input.",
            provider_model.name,
        )
    return success


def verify_model_translation(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify translation capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_translation()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TRANSLATION
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.base_url = provider_model.provider.base_url

        response = openai.chat.completions.create(
            model=provider_model.name,
            messages=[{"role": "user", "content": "Translate this to Spanish: Hello"}],
            max_completion_tokens=VERIFICATION_MAX_COMPLETION_TOKENS,
        )
        content = completion_text(response).lower()
        success = "hola" in content
        if not success:
            logger.error(
                "%s provider model %s did not translate 'Hello' to Spanish. finish_reason: %s, response: %s",
                prefix,
                provider_model.name,
                response.choices[0].finish_reason,
                content[:200],
            )
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error(
            "Error during verify_model_translation() for provider model %s", provider_model.name, exc_info=True
        )
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_summarization(provider_model: ProviderModel, **kwargs) -> bool:
    """Verify summarization capabilities of the provider model."""
    success = False
    prefix = SmarterFormattedText.text(module_prefix + "verify_summarization()")
    logger.debug("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.SUMMARIZATION
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.api_key = provider_model.provider.api_key.get_secret(update_last_accessed=False)
        openai.base_url = provider_model.provider.base_url

        long_text = (
            "OpenAI is an AI research and deployment company. "
            "Our mission is to ensure that artificial general intelligence benefits all of humanity. "
            "We are committed to ensuring that artificial general intelligence—AI systems that are generally smarter than humans—"
            "benefits all of humanity. We will build safe and beneficial AGI, or help others achieve this goal."
        )
        response = openai.chat.completions.create(
            model=provider_model.name,
            messages=[{"role": "user", "content": f"Summarize this into 10 words or less: {long_text}"}],
            max_completion_tokens=VERIFICATION_MAX_COMPLETION_TOKENS,
        )
        summary = completion_text(response)
        success = 0 < len(summary.split()) <= 10
        if not success:
            logger.error(
                "%s provider model %s did not summarize the text in 10 words or less. finish_reason: %s, response: %s",
                prefix,
                provider_model.name,
                response.choices[0].finish_reason,
                summary[:200],
            )
    except Exception as e:
        raise_if_inconclusive(e)
        logger.error(
            "Error during verify_model_summarization() for provider model %s", provider_model.name, exc_info=True
        )
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_provider_model(provider_model_id, **kwargs):
    """
    Run every check that the provider model's ``supports_*`` fields call for, then activate or deactivate it.

    A model that passes every check is activated, and one that fails any is deactivated. When a check's
    provider error is about the account or the provider rather than the model (see :func:`raise_if_inconclusive`),
    the run stops and the model is left as it was.

    :param provider_model_id: The id of the :class:`~smarter.apps.provider.models.ProviderModel` to verify.
    """

    try:
        provider_model = ProviderModel.objects.get(id=provider_model_id)
    except ProviderModel.DoesNotExist:
        logger.error(
            "%s Provider model with id %s does not exist",
            SmarterFormattedText.text(module_prefix + "verify_provider_model()"),
            provider_model_id,
        )
        return

    if provider_model.provider.api_key is None:
        # a built-in Provider is created without a key when its environment variable is not set. Its
        # models cannot be verified, and must not be deactivated, until it has one: see initialize_providers.
        logger.warning(
            "%s skipped provider model %s: its provider %s has no API key.",
            SmarterFormattedText.text(module_prefix + "verify_provider_model()"),
            provider_model.name,
            provider_model.provider.name,
        )
        return

    # blackball method
    success: bool = True

    try:
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
    except ProviderModelVerificationInconclusive as e:
        logger.warning(
            "%s verification of provider model %s is inconclusive, so it remains %s. The provider said: %s",
            SmarterFormattedText.text(module_prefix + "verify_provider_model()"),
            provider_model.name,
            "active" if provider_model.is_active else "inactive",
            e,
        )
        return

    if success:
        provider_model.is_active = True
        provider_model.save(update_fields=["is_active"])
        model_verification_success.send(sender=ProviderModel, provider_model=provider_model)
        logger.debug("Verification tests succeeded for provider model: %s", provider_model.name)
    else:
        provider_model.is_active = False
        provider_model.save(update_fields=["is_active"])
        model_verification_failure.send(sender=ProviderModel, provider_model=provider_model)
        logger.error("One or more verification tests failed for provider model: %s", provider_model.name)
