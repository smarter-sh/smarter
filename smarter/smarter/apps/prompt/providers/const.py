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
    TOOL_CALL_ID = "tool_call_id"

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
    MAX_COMPLETION_TOKENS_KEY = "max_completion_tokens"
    TEMPERATURE_KEY = "temperature"
    all = [MODEL_KEY, TOOLS_KEY, MESSAGES_KEY, MAX_COMPLETION_TOKENS_KEY, TEMPERATURE_KEY]


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
    "babbage-002",
    "chatgpt-4o-latest",
    "codex-mini-latest",
    "computer-use-preview",
    "computer-use-preview-2025-03-11",
    "davinci-002",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-instruct",
    "gpt-3.5-turbo-instruct-0914",
    "gpt-4",
    "gpt-4-0125-preview",
    "gpt-4-0613",
    "gpt-4-1106-preview",
    "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-turbo-preview",
    "gpt-4.1",
    "gpt-4.1-2025-04-14",
    "gpt-4.1-mini",
    "gpt-4.1-mini-2025-04-14",
    "gpt-4.1-nano",
    "gpt-4.1-nano-2025-04-14",
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o-audio-preview",
    "gpt-4o-audio-preview-2024-10-01",
    "gpt-4o-audio-preview-2024-12-17",
    "gpt-4o-audio-preview-2025-06-03",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-mini-audio-preview",
    "gpt-4o-mini-audio-preview-2024-12-17",
    "gpt-4o-mini-realtime-preview",
    "gpt-4o-mini-realtime-preview-2024-12-17",
    "gpt-4o-mini-search-preview",
    "gpt-4o-mini-search-preview-2025-03-11",
    "gpt-4o-mini-transcribe",
    "gpt-4o-mini-tts",
    "gpt-4o-realtime-preview",
    "gpt-4o-realtime-preview-2024-10-01",
    "gpt-4o-realtime-preview-2024-12-17",
    "gpt-4o-realtime-preview-2025-06-03",
    "gpt-4o-search-preview",
    "gpt-4o-search-preview-2025-03-11",
    "gpt-4o-transcribe",
    "gpt-5",
    "gpt-5-2025-08-07",
    "gpt-5-chat-latest",
    "gpt-5-mini",
    "gpt-5-mini-2025-08-07",
    "gpt-5-nano",
    "gpt-5-nano-2025-08-07",
    "gpt-audio",
    "gpt-audio-2025-08-28",
    "gpt-image-1",
    "gpt-realtime",
    "gpt-realtime-2025-08-28",
    "o1",
    "o1-2024-12-17",
    "o1-mini",
    "o1-mini-2024-09-12",
    "o1-pro",
    "o1-pro-2025-03-19",
    "o3",
    "o3-2025-04-16",
    "o3-mini",
    "o3-mini-2025-01-31",
    "o4-mini",
    "o4-mini-2025-04-16",
    "o4-mini-deep-research",
    "o4-mini-deep-research-2025-06-26",
    "omni-moderation-2024-09-26",
    "omni-moderation-latest",
    "tts-1",
    "tts-1-1106",
    "tts-1-hd",
    "tts-1-hd-1106",
]

VALID_EMBEDDING_MODELS = [
    "text-embedding-ada-002",
    "text-similarity-*-001",
    "text-search-*-*-001",
    "code-search-*-*-001",
]
