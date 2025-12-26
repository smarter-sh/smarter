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
    MAX_TOKENS = "max_completion_tokens"
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


class SAMProviderSpecKeys(SmarterEnumAbstract):
    """Smarter API Provider Manifest Specification Keys enumeration."""

    PROVIDER = "provider"
    CONFIG = "config"

    NAME = "name"
    DESCRIPTION = "description"
    STATUS = "status"
    IS_ACTIVE = "is_active"
    IS_VERIFIED = "is_verified"
    IS_FEATURED = "is_featured"
    IS_DEPRECATED = "is_deprecated"
    IS_FLAGGED = "is_flagged"
    IS_SUSPENDED = "is_suspended"
    BASE_URL = "base_url"
    API_KEY = "api_key"
    CONNECTIVITY_TEST_PATH = "connectivity_test_path"
    LOGO = "logo"
    WEBSITE_URL = "website_url"
    OWNERSHIP_REQUESTED = "ownership_requested"
    CONTACT_EMAIL = "contact_email"
    CONTACT_EMAIL_VERIFIED = "contact_email_verified"
    SUPPORT_EMAIL = "support_email"
    SUPPORT_EMAIL_VERIFIED = "support_email_verified"
    DOCS_URL = "docs_url"
    TERMS_OF_SERVICE_URL = "terms_of_service_url"
    PRIVACY_POLICY_URL = "privacy_policy_url"
    TOS_ACCEPTED_AT = "tos_accepted_at"
    TOS_ACCEPTED_BY = "tos_accepted_by"
