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
    DEFAULT_MODEL = "default_model"
    MAX_TOKENS = "max_tokens"
    TEMPERATURE = "temperature"
    TOP_P = "top_p"
    VALID_CHAT_COMPLETION_MODELS = "valid_chat_completion_models"
