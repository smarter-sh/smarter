"""
Constants for the OpenAI provider.
"""

import openai


# pylint: disable=too-few-public-methods
class OpenAIObjectTypes:
    """V1 API Object Types (replace OpeanAIEndPoint)"""

    Embedding = "embedding"
    ChatCompletion = "chat.completion"
    Moderation = "moderation"
    Image = "image"
    Audio = "audio"
    Models = "models"
    all_object_types = [Embedding, ChatCompletion, Moderation, Image, Audio, Models]


# pylint: disable=too-few-public-methods
class OpenAIEndPoint:
    """
    A class representing an endpoint for the OpenAI API.

    Attributes:
        api_key (str): The API key to use for authentication.
        endpoint (str): The URL of the OpenAI API endpoint.
    """

    Embedding = openai.Embedding.__name__  # type: ignore[assignment]
    ChatCompletion = "chat/completions"
    Moderation = openai.Moderation.__name__  # type: ignore[assignment]
    Image = openai.Image.__name__  # type: ignore[assignment]
    Audio = openai.Audio.__name__  # type: ignore[assignment]
    Models = openai.Model.__name__  # type: ignore[assignment]
    all_endpoints = [Embedding, ChatCompletion, Moderation, Image, Audio, Models]


# pylint: disable=too-few-public-methods
class OpenAIMessageKeys:
    """A class representing the keys for a message in the OpenAI API."""

    MESSAGE_ROLE_KEY = "role"
    MESSAGE_CONTENT_KEY = "content"
    MESSAGE_NAME_KEY = "name"

    SYSTEM_MESSAGE_KEY = "system"
    ASSISTANT_MESSAGE_KEY = "assistant"
    USER_MESSAGE_KEY = "user"
    TOOL_MESSAGE_KEY = "tool"

    SMARTER_MESSAGE_KEY = "smarter"

    # the valid openai api message keys
    all = [
        SYSTEM_MESSAGE_KEY,
        ASSISTANT_MESSAGE_KEY,
        USER_MESSAGE_KEY,
        TOOL_MESSAGE_KEY,
    ]
    # on first completions openai does not allow requests that include tool responses
    no_tools = [
        SYSTEM_MESSAGE_KEY,
        ASSISTANT_MESSAGE_KEY,
        USER_MESSAGE_KEY,
    ]
    all_openai_roles = [SYSTEM_MESSAGE_KEY, ASSISTANT_MESSAGE_KEY, USER_MESSAGE_KEY, TOOL_MESSAGE_KEY]
    all_roles = [SYSTEM_MESSAGE_KEY, ASSISTANT_MESSAGE_KEY, USER_MESSAGE_KEY, TOOL_MESSAGE_KEY, SMARTER_MESSAGE_KEY]


class OpenAIRequestKeys:
    """A class representing the keys for a request in the OpenAI API."""

    MODEL_KEY = "model"
    TOOLS_KEY = "tools"
    MESSAGES_KEY = "messages"
    MAX_TOKENS_KEY = "max_tokens"
    TEMPERATURE_KEY = "temperature"
    all = [MODEL_KEY, TOOLS_KEY, MESSAGES_KEY, MAX_TOKENS_KEY, TEMPERATURE_KEY]


class OpenAIResponseKeys:
    """A class representing the keys for a response in the OpenAI API."""

    ID_KEY = "id"
    MODEL_KEY = "model"
    USAGE_KEY = "usage"
    OBJECT_KEY = "object"
    CHOICES_KEY = "choices"
    CREATED_KEY = "created"
    METADATA_KEY = "metadata"
    SERVICE_TIER = "service_tier"
    SYSTEM_FINGERPRINT = "system_fingerprint"

    all = [
        ID_KEY,
        MODEL_KEY,
        USAGE_KEY,
        OBJECT_KEY,
        CHOICES_KEY,
        CREATED_KEY,
        METADATA_KEY,
        SERVICE_TIER,
        SYSTEM_FINGERPRINT,
    ]


class OpenAIResponseChoices:
    """A class representing the keys for a response in the OpenAI API."""

    INDEX_KEY = "index"
    MESSAGE_KEY = "message"
    LOGPROBS_KEY = "logprobs"
    FINISH_REASON_KEY = "finish_reason"

    all = [INDEX_KEY, MESSAGE_KEY, LOGPROBS_KEY, FINISH_REASON_KEY]


class OpenAIResponseChoicesMessage:
    """A class representing the keys for a response choice message in the OpenAI API."""

    ROLE_KEY = "role"
    AUDIO_KEY = "audio"
    CONTENT_KEY = "content"
    REFUSAL_KEY = "refusal"
    TOOL_CALLS_KEY = "tool_calls"
    FUNCTION_CALL_KEY = "function_call"
    all = [ROLE_KEY, AUDIO_KEY, CONTENT_KEY, REFUSAL_KEY, TOOL_CALLS_KEY, FUNCTION_CALL_KEY]


VALID_CHAT_COMPLETION_MODELS = [
    "o1",
    "o1-mini",
    "o1-preview",
    "gpt-4o",
    "gpt-5-nano",
    "chatgpt-4o-latest",
    "gpt-4",
    "gpt-5-nano",
    "o1-preview",
    "o1-mini",
]

VALID_EMBEDDING_MODELS = [
    "text-embedding-ada-002",
    "text-similarity-*-001",
    "text-search-*-*-001",
    "code-search-*-*-001",
]
