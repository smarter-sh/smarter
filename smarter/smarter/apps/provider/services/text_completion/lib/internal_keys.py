"""
Internal keys used in the chat provider.
"""

SMARTER_SYSTEM_KEY_PREFIX = "smarter_"


class _InternalKeys:
    """
    Internal dict keys used in the chat provider.
    """

    REQUEST_KEY = "request"
    RESPONSE_KEY = "response"
    TOOLS_KEY = "tools"
    MESSAGES_KEY = "messages"
    PLUGINS_KEY = "plugins"
    MODEL_KEY = "model"
    API_URL = "api_url"
    API_KEY = "api_key"
    TEMPERATURE_KEY = "temperature"
    MAX_COMPLETION_TOKENS_KEY = "max_completion_tokens"
    TOOL_CHOICE = "tool_choice"

    SMARTER_PLUGIN_KEY = SMARTER_SYSTEM_KEY_PREFIX + "plugin"
    SMARTER_IS_NEW = SMARTER_SYSTEM_KEY_PREFIX + "is_new"


__all__ = ["_InternalKeys"]
