"""Smarter API PLugin Manifest - enumerated datatypes."""

from typing import List, TypedDict

from smarter.common.enum import SmarterEnumAbstract


###############################################################################
# Enums for manifest keys in error handlers and other on-screen messages
###############################################################################
class ProviderModelEnum(SmarterEnumAbstract):
    """Smarter Provider Model enumeration.
    supports_streaming = models.BooleanField(default=False, blank=False, null=False)
    supports_tools = models.BooleanField(default=False, blank=False, null=False)
    supports_text_input = models.BooleanField(default=True, blank=False, null=False)
    supports_image_input = models.BooleanField(default=False, blank=False, null=False)
    supports_audio_input = models.BooleanField(default=False, blank=False, null=False)
    supports_embedding = models.BooleanField(default=False, blank=False, null=False)
    supports_fine_tuning = models.BooleanField(default=False, blank=False, null=False)
    supports_search = models.BooleanField(default=False, blank=False, null=False)
    supports_code_interpreter = models.BooleanField(default=False, blank=False, null=False)
    supports_image_generation = models.BooleanField(default=False, blank=False, null=False)
    supports_audio_generation = models.BooleanField(default=False, blank=False, null=False)
    supports_text_generation = models.BooleanField(default=True, blank=False, null=False)
    supports_translation = models.BooleanField(default=False, blank=False, null=False)
    supports_summarization = models.BooleanField(default=False, blank=False, null=False)

    """

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


class ProviderModelTypedDict(TypedDict):
    """TypedDict for provider model information."""

    api_key: str
    provider_name: str
    provider_id: int
    base_url: str
    model: str
    max_tokens: int
    temperature: float
    top_p: float
    supports_streaming: bool
    supports_tools: bool
    supports_text_input: bool
    supports_image_input: bool
    supports_audio_input: bool
    supports_embedding: bool
    supports_fine_tuning: bool
    supports_search: bool
    supports_code_interpreter: bool
    supports_image_generation: bool
    supports_audio_generation: bool
    supports_text_generation: bool
    supports_translation: bool
    supports_summarization: bool
