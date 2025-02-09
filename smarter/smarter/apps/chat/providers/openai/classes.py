"""
OpenAI chat provider.
"""

import logging

# smarter stuff
from smarter.apps.chat.providers.base_classes import OpenAICompatibleChatProvider
from smarter.common.conf import settings as smarter_settings

# smarter chat provider stuff
from ..const import VALID_CHAT_COMPLETION_MODELS


BASE_URL = "https://api.openai.com/v1/"  # don't forget the trailing slash
PROVIDER_NAME = "openai"
DEFAULT_MODEL = "gpt-4o-mini"


logger = logging.getLogger(__name__)


class OpenAIChatProvider(OpenAICompatibleChatProvider):
    """
    OpenAI chat provider.
    """

    def __init__(self):
        super().__init__(
            provider=PROVIDER_NAME,
            base_url=BASE_URL,
            api_key=smarter_settings.openai_api_key.get_secret_value(),
            default_model=DEFAULT_MODEL,
            default_system_role=smarter_settings.llm_default_system_role,
            default_temperature=smarter_settings.llm_default_temperature,
            default_max_tokens=smarter_settings.llm_default_max_tokens,
            valid_chat_completion_models=VALID_CHAT_COMPLETION_MODELS,
            add_built_in_tools=True,
        )
