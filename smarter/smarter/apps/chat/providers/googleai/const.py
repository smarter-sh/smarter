BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
PROVIDER_NAME = "googleai"
DEFAULT_MODEL = "gemini-1.5-flash"


# https://ai.google.dev/gemini-api/docs/models/gemini
VALID_CHAT_COMPLETION_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash	",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "aqa",
]


# pylint: disable=too-few-public-methods
class GoogleAIMessageKeys:
    """A class representing the keys for a message in the OpenAI API."""

    MESSAGE_ROLE_KEY = "role"
    MESSAGE_CONTENT_KEY = "content"
    USER_MESSAGE_KEY = "user"
    ASSISTANT_MESSAGE_KEY = "model"
    SYSTEM_MESSAGE_KEY = "system"
    all = [
        SYSTEM_MESSAGE_KEY,
        USER_MESSAGE_KEY,
        ASSISTANT_MESSAGE_KEY,
    ]
