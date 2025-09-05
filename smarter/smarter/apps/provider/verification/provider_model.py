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
import logging
import wave

import openai

from smarter.apps.provider.models import ProviderModel, ProviderModelVerificationTypes
from smarter.apps.provider.signals import (
    model_verification_failure,
    model_verification_success,
)
from smarter.apps.provider.utils import (
    get_model_verification_for_type,
    set_model_verification,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PROVIDER_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

module_prefix = "smarter.apps.provider.verification.provider_model."


def verify_model_streaming(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify streaming capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_steaming()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.STREAMING
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.base_url = provider_model.provider.base_url
        openai.api_key = (provider_model.provider.api_key.get_secret(update_last_accessed=False),)
        response = openai.chat.completions.create(
            model=provider_model.name,
            messages=[{"role": "user", "content": "Hello"}],
            stream=True,
            max_tokens=10,
        )
        # Try to get the first chunk from the stream
        first_chunk = next(iter(response), None)
        success = first_chunk is not None
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_tools(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify tools capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_tools()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TOOLS
    )
    if provider_model_verification.is_valid:
        return True

    try:
        openai.base_url = provider_model.provider.base_url
        openai.api_key = (provider_model.provider.api_key.get_secret(update_last_accessed=False),)
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
            max_tokens=10,
        )
        success = True
    except Exception:
        success = False

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

    try:
        openai.base_url = provider_model.provider.base_url
        openai.api_key = (provider_model.provider.api_key.get_secret(update_last_accessed=False),)
        openai.chat.completions.create(
            model=provider_model.name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
        )
        success = True
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_image_input(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify image input capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_image_input()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.IMAGE_INPUT
    )
    if provider_model_verification.is_valid:
        return True

    try:
        # Example: using a small PNG image as base64 (replace with a real image in production)
        dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgQnQn1wAAAAASUVORK5CYII="
        openai.base_url = provider_model.provider.base_url
        openai.api_key = (provider_model.provider.api_key.get_secret(update_last_accessed=False),)
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
            max_tokens=5,
        )
        success = True
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_audio_input(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify audio input capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_audio_input()")
    logger.info("%s for provider model: %s", prefix, provider_model)

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
        openai.audio.transcriptions.create(
            model=provider_model.name, file=buffer, filename="test.wav", mime_type="audio/wav"
        )
        success = True
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_fine_tuning(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify fine-tuning capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_fine_tuning()")
    logger.info("%s for provider model: %s", prefix, provider_model)

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
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_search(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify search capabilities of the provider model.
    DEPRECATED: OpenAI has deprecated the search endpoint.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_search()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.SEARCH
    )

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_code_interpreter(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify code interpreter capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_code_interpreter()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.CODE_INTERPRETER
    )
    if provider_model_verification.is_valid:
        return True

    # List of known models that support code interpreter as of June-2025
    code_interpreter_models = [
        "gpt-4o",
        "gpt-5-nano",
    ]

    success = provider_model.name in code_interpreter_models

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_image(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify text to image capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_text_to_image()")
    logger.info("%s for provider model: %s", prefix, provider_model)

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
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_audio(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify text to audio capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_text_to_audio()")
    logger.info("%s for provider model: %s", prefix, provider_model)

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
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_text_to_text(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify text to text capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_text_to_text()")
    logger.info("%s for provider model: %s", prefix, provider_model)

    provider_model_verification = get_model_verification_for_type(
        provider_model=provider_model, verification_type=ProviderModelVerificationTypes.TEXT_TO_TEXT
    )
    if provider_model_verification.is_valid:
        return True

    success = verify_model_text_input(provider_model=provider_model)

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_translation(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify translation capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_translation()")
    logger.info("%s for provider model: %s", prefix, provider_model)

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
            max_tokens=10,
        )
        content = response.choices[0].message.content.strip().lower()
        success = "hola" in content
    except Exception:
        success = False

    set_model_verification(provider_model_verification=provider_model_verification, is_successful=success)
    return success


def verify_model_summarization(provider_model: ProviderModel, **kwargs) -> bool:
    """
    Verify summarization capabilities of the provider model.
    """
    success = False
    prefix = formatted_text(module_prefix + "verify_summarization()")
    logger.info("%s for provider model: %s", prefix, provider_model)

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
            max_tokens=30,
        )
        summary = response.choices[0].message.content.strip()
        success = len(summary) <= 10
    except Exception:
        success = False

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
