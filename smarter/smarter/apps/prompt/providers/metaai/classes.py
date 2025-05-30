"""
Meta AI chat provider.
"""

import logging

# smarter stuff
from smarter.apps.prompt.providers.base_classes import OpenAICompatibleChatProvider
from smarter.common.conf import settings as smarter_settings

# smarter chat provider stuff
from .const import BASE_URL, DEFAULT_MODEL, PROVIDER_NAME, VALID_CHAT_COMPLETION_MODELS


logger = logging.getLogger(__name__)


class MetaAIChatProvider(OpenAICompatibleChatProvider):
    """
    MetaAI chat provider.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            provider=PROVIDER_NAME,
            base_url=BASE_URL,
            api_key=smarter_settings.llama_api_key.get_secret_value(),
            default_model=DEFAULT_MODEL,
            default_system_role=smarter_settings.llm_default_system_role,
            default_temperature=smarter_settings.llm_default_temperature,
            default_max_tokens=smarter_settings.llm_default_max_tokens,
            valid_chat_completion_models=VALID_CHAT_COMPLETION_MODELS,
            add_built_in_tools=False,
            **kwargs,
        )
