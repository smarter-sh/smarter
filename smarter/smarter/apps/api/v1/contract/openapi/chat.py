"""
The chat api, under ``/api/v1/llm-clients/{id}/``: what Smarter Chat and the SDKs call to chat with an LLMClient.

Its requests and responses are the Smarter Chat api contract's, version 2
(:mod:`smarter.apps.prompt.contract.models`).
"""

from smarter.apps.api.v1.contract.models import (
    OpenApiMediaType,
    OpenApiOperation,
    OpenApiParameter,
    OpenApiPathItem,
    OpenApiRequestBody,
    OpenApiResponse,
    OpenApiTag,
)
from smarter.apps.api.v1.contract.openapi.families.llmclient import (
    LLMCLIENT_ID_PARAMETER,
    LLMCLIENTS,
)
from smarter.apps.prompt.contract.const import CHAT_CONTRACT_V2_CAPABILITY
from smarter.apps.prompt.contract.models import (
    PromptChatApiConfigRequest,
    PromptChatApiConfigResponse,
    PromptChatApiErrorResponse,
    PromptChatApiProgressEvent,
    PromptChatApiProgressResult,
    PromptChatApiPromptRequest,
    PromptChatApiPromptResponse,
    PromptChatApiProviderRequestResponse,
)

from .builders import json_response, ref

TAG_CHAT = "chat"
"""The tag of the chat api's operations, and of the cli's prompt commands."""

CHAT_TAG = OpenApiTag(name=TAG_CHAT, description=f"Chats with {LLMCLIENTS.plural}.")
"""The document's tag of the chat api."""

SESSION_KEY_PARAMETER = OpenApiParameter(
    name="session_key",
    in_="query",
    required=False,
    description="The chat session's key. The platform looks for it in this parameter, then in the request "
    "body, a header and a cookie, in that order.",
    schema_={"type": "string", "pattern": "^[a-f0-9]{64}$"},
)


CAPABILITIES_PARAMETER = OpenApiParameter(
    name="X-Smarter-Capabilities",
    in_="header",
    required=False,
    description=f"A comma-separated list of the client's capabilities. {CHAT_CONTRACT_V2_CAPABILITY} asks for "
    "version 2 of the Smarter Chat api contract, which this document describes, and which is also the "
    "default. chat-contract-v1 asks for the deprecated version 1.",
    schema_={"type": "string", "default": CHAT_CONTRACT_V2_CAPABILITY},
)


VERBOSE_CONFIG_PARAMETER = OpenApiParameter(
    name="verbose",
    in_="query",
    required=False,
    description="true adds the configuration's diagnostic parts: the session's tool calls "
    "(history.prompt_tool_call_history), the complete meta_data, and the lists of the "
    f"{LLMCLIENTS.resource}'s plugins and "
    "extensions. Without it, the configuration has what a chat needs, and the counts of the plugins and "
    f"extensions. A deployed {LLMCLIENTS.resource}'s own host ignores it.",
    schema_={"type": "boolean", "default": False},
)


ACCEPT_PARAMETER = OpenApiParameter(
    name="Accept",
    in_="header",
    required=False,
    description="text/event-stream streams the prompt's progress as Server-Sent Events. Otherwise, the "
    "response is the prompt's JSON.",
    schema_={"type": "string", "default": "application/json"},
)


def chat_paths() -> dict[str, OpenApiPathItem]:
    """
    The chat api's paths, relative to the server's ``/api/v1``.

    The prompt's ``200`` response is JSON, or, for a client that accepts ``text/event-stream``, a
    stream of Server-Sent Events: ``progress`` events, then one ``result`` event, whose ``response``
    is the JSON that a non-streaming client receives. OpenAPI 3.1 can't type the events of a stream,
    so the stream's media type names their schemas in an ``x-smarter-events`` extension.

    :returns: The paths, e.g. ``{"/llm-clients/{id}/prompt/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = LLMCLIENTS
    parameters = [LLMCLIENT_ID_PARAMETER, SESSION_KEY_PARAMETER, CAPABILITIES_PARAMETER]
    config = OpenApiOperation(
        operationId=family.operation_id("config"),
        summary=f"{family.a_capitalized}'s chat configuration",
        description=f"The configuration of a chat with {family.a}, and a chat session: a new one, or the one "
        "whose key is sent. Its session_key identifies the session in the following prompts, and "
        "url_llmclient is where to send them.",
        tags=[TAG_CHAT],
        parameters=[*parameters, VERBOSE_CONFIG_PARAMETER],
        requestBody=OpenApiRequestBody(
            required=False,
            content={"application/json": OpenApiMediaType(schema_=ref(PromptChatApiConfigRequest.__name__))},
        ),
        responses={
            "200": json_response("The configuration.", PromptChatApiConfigResponse.__name__),
            "default": json_response(
                f"An error, e.g. 404 for {family.a} that does not exist, or that the user may not read.",
                PromptChatApiErrorResponse.__name__,
            ),
        },
    )
    prompt = OpenApiOperation(
        operationId=family.operation_id("prompt"),
        summary=f"Prompt {family.a}",
        description="Run a prompt: the platform selects plugins, calls the LLM, runs the tools that the LLM "
        "calls, and applies the Guardrails, then returns the messages that the prompt added to the chat. "
        "Prompts are billed by the LLM provider. A streaming client receives progress events while the prompt "
        "runs, then the result, whose status is the prompt's http status.",
        tags=[TAG_CHAT],
        parameters=[*parameters, ACCEPT_PARAMETER],
        requestBody=OpenApiRequestBody(
            required=True,
            content={"application/json": OpenApiMediaType(schema_=ref(PromptChatApiPromptRequest.__name__))},
        ),
        responses={
            "200": OpenApiResponse(
                description="The prompt's result, as JSON, or as a stream of Server-Sent Events.",
                content={
                    "application/json": OpenApiMediaType(schema_=ref(PromptChatApiPromptResponse.__name__)),
                    "text/event-stream": OpenApiMediaType(
                        schema_={
                            "type": "string",
                            "description": "Server-Sent Events: retry, then a progress event per step, keepalive "
                            "comments while the prompt waits, and a result event, last. Each event's data is JSON.",
                        },
                        x_smarter_events={
                            "progress": ref(PromptChatApiProgressEvent.__name__),
                            "result": ref(PromptChatApiProgressResult.__name__),
                        },
                    ),
                },
            ),
            "default": json_response("An error.", "LLMClientPromptErrorResponse"),
        },
    )
    provider_request = OpenApiOperation(
        operationId=family.operation_id("provider_request"),
        summary="A chat session's request to the LLM provider",
        description="The chat session's conversation, as the request body that Smarter sends to the LLM "
        "provider's v1/chat/completions api: the model, temperature, token limit and tools of its latest prompt "
        f"(or the {family.resource}'s, before its first prompt), and its system, user, assistant and tool messages, "
        "without Smarter's own messages, fields, api url or key. It can be sent with curl, or to the Prompt "
        f"Passthrough api. Only a user who may read the {family.resource} receives it, never a deployed "
        f"{family.resource}'s own host.",
        tags=[TAG_CHAT],
        parameters=[LLMCLIENT_ID_PARAMETER, SESSION_KEY_PARAMETER],
        requestBody=OpenApiRequestBody(
            required=False,
            content={"application/json": OpenApiMediaType(schema_=ref(PromptChatApiConfigRequest.__name__))},
        ),
        responses={
            "200": json_response("The request body.", PromptChatApiProviderRequestResponse.__name__),
            "default": json_response(
                f"An error, e.g. 404 for {family.a} that does not exist, or that the user may not read.",
                PromptChatApiErrorResponse.__name__,
            ),
        },
    )
    return {
        family.path("{id}/config/"): OpenApiPathItem(post=config),
        family.path("{id}/prompt/"): OpenApiPathItem(post=prompt),
        family.path("{id}/provider-request/"): OpenApiPathItem(post=provider_request),
    }


__all__ = ["CHAT_TAG", "TAG_CHAT", "chat_paths"]
