"""Constants for the OpenAI provider."""


# pylint: disable=too-few-public-methods
class OpenAIObjectTypes:
    """V1 API Object Types (replace OpeanAIEndPoint)."""

    ChatCompletion = "prompt.completion"

    # removed in openai>=1.0.0 - see the README at https://github.com/openai/openai-python for the API.
    # -------------------------------------------------------------------------
    # Embedding = "embedding"
    # Audio = "audio"
    # Image = "image"
    # Models = "models"
    # Moderation = "moderation"
    all_object_types = [ChatCompletion]


# pylint: disable=too-few-public-methods
class OpenAIEndPoint:
    """
    A class representing an endpoint for the OpenAI API.

    Attributes:
        api_key (str): The API key to use for authentication.
        endpoint (str): The URL of the OpenAI API endpoint.
    """

    ChatCompletion = "prompt/completions"

    # removed in openai>=1.0.0 - see the README at https://github.com/openai/openai-python for the API.
    # -------------------------------------------------------------------------
    # Moderation = openai.Moderation.__name__  # type: ignore[assignment]
    # Image = openai.Image.__name__  # type: ignore[assignment]
    # Audio = openai.Audio.__name__  # type: ignore[assignment]
    # Models = openai.Model.__name__  # type: ignore[assignment]
    all_endpoints = [ChatCompletion]


# pylint: disable=too-few-public-methods
class OpenAIMessageKeys:
    """A class representing the keys for a message in the OpenAI API."""

    # valid openai api message keys
    MESSAGE_ROLE_KEY = "role"
    MESSAGE_CONTENT_KEY = "content"
    MESSAGE_NAME_KEY = "name"
    SYSTEM_MESSAGE_KEY = "system"
    ASSISTANT_MESSAGE_KEY = "assistant"
    USER_MESSAGE_KEY = "user"
    TOOL_MESSAGE_KEY = "tool"
    TOOL_CALL_ID = "tool_call_id"

    # proprietary smarter message keys that are not sent to openai but are used
    # internally to track messages in prompt engineer workbench conversations.
    SMARTER_MESSAGE_KEY = "smarter"
    SMARTER_ERROR_KEY = "smarter_error"

    # valid openai api message keys
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
    # valid keys to include in api prompt requests to openai
    all_openai_roles = [SYSTEM_MESSAGE_KEY, ASSISTANT_MESSAGE_KEY, USER_MESSAGE_KEY, TOOL_MESSAGE_KEY]

    # all valid keys that can be used in messages in prompt engineer workbench
    # conversations, including proprietary smarter keys.
    all_roles = [
        SYSTEM_MESSAGE_KEY,
        ASSISTANT_MESSAGE_KEY,
        USER_MESSAGE_KEY,
        TOOL_MESSAGE_KEY,
        SMARTER_MESSAGE_KEY,
        SMARTER_ERROR_KEY,
    ]


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


# OpenAI's chat models: the models that its v1/chat/completions endpoint accepts, and that are not
# deprecated. Plugin manifests' spec.prompt.model is validated against this list. Reviewed 2026-10-04
# against https://api.openai.com/v1/models, and https://developers.openai.com/api/docs/deprecations.
# A model alias is removed when all of its dated snapshots are deprecated, e.g. gpt-5 and o3. Models
# that only the Responses API serves, such as gpt-5.5-pro, and audio, image, realtime, moderation and
# embedding models, are not chat models.
VALID_CHAT_COMPLETION_MODELS = [
    "chat-latest",
    "gpt-4.1",
    "gpt-4.1-2025-04-14",
    "gpt-4.1-mini",
    "gpt-4.1-mini-2025-04-14",
    "gpt-4o",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    "gpt-5-search-api",
    "gpt-5-search-api-2025-10-14",
    "gpt-5.2",
    "gpt-5.2-2025-12-11",
    "gpt-5.4",
    "gpt-5.4-2026-03-05",
    "gpt-5.4-mini",
    "gpt-5.4-mini-2026-03-17",
    "gpt-5.5",
    "gpt-5.5-2026-04-23",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-6-astra",
    "gpt-6-luna",
    "gpt-6-sol",
    "gpt-6.1-sol",
]

# OpenAI's embedding models that are not deprecated. Reviewed 2026-10-04, as above.
VALID_EMBEDDING_MODELS = [
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
]
