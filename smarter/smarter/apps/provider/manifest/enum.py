"""Smarter API PLugin Manifest - enumerated datatypes."""

from smarter.common.enum import SmarterEnumAbstract


###############################################################################
# Enums for manifest keys in error handlers and other on-screen messages
###############################################################################
class ProviderModelEnum(SmarterEnumAbstract):
    """Smarter Provider Model enumeration."""

    API_KEY = "api_key"
    PROVIDER_NAME = "provider_name"
    PROVIDER_ID = "provider_id"
    BASE_URL = "base_url"
    MODEL = "model"
    MAX_TOKENS = "max_tokens"
    TEMPERATURE = "temperature"
    TOP_P = "top_p"

    SUPPORTS_STREAMING = "supports_streaming"
    SUPPORTS_TOOLS = "supports_tools"
    SUPPORTS_TEXT_INPUT = "supports_text_input"
    SUPPORTS_IMAGE_INPUT = "supports_image_input"
    SUPPORTS_AUDIO_INPUT = "supports_audio_input"
    SUPPORTS_EMBEDDING = "supports_embedding"
    SUPPORTS_FINE_TUNING = "supports_fine_tuning"
    SUPPORTS_SEARCH = "supports_search"
    SUPPORTS_CODE_INTERPRETER = "supports_code_interpreter"
    SUPPORTS_IMAGE_GENERATION = "supports_image_generation"
    SUPPORTS_AUDIO_GENERATION = "supports_audio_generation"
    SUPPORTS_TEXT_GENERATION = "supports_text_generation"
    SUPPORTS_TRANSLATION = "supports_translation"
    SUPPORTS_SUMMARIZATION = "supports_summarization"
