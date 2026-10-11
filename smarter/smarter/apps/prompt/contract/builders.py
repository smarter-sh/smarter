"""
Builders of the Smarter Chat api contract's responses.

The configuration view builds a :class:`~.models.PromptChatApiConfig`, whose methods derive its responses.
These functions serve both views, and turn a prompt's result into what the client receives:

- :func:`requested_contract` reads the version of the contract that the client asked for.
- :func:`without_diagnostics` removes the complete LLM requests and responses from a prompt's result.
- :func:`prompt_result_v2` turns a prompt's result into version 2.
- :func:`chat_error_response` is the one error response of both apis.
"""

import json
from http import HTTPStatus
from typing import Any, Optional

from django.http import HttpRequest

from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse

from .const import (
    CAPABILITIES_HEADER,
    CHAT_CONTRACT_V1,
    CHAT_CONTRACT_V1_CAPABILITY,
    CHAT_CONTRACT_V2,
    CHAT_CONTRACT_V2_CAPABILITY,
    CLIENT_HEADER,
    DEFAULT_CHAT_CONTRACT,
    DIAGNOSTIC_COMPLETION_KEYS,
    DIAGNOSTIC_COMPLETION_TOP_KEYS,
    LEGACY_CHAT_CLIENT,
)
from .models import (
    PromptChatApiCompletion,
    PromptChatApiErrorBody,
    PromptChatApiPromptResult,
)

SMARTER_KEY = "smarter"


class PromptChatApiError(Exception):
    """The base class of the errors that the configuration and prompt apis return."""

    status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class PromptChatApiErrorNotFound(PromptChatApiError):
    """The LLMClient doesn't exist, or the client may not use it."""

    status = HTTPStatus.NOT_FOUND.value


class PromptChatApiErrorForbidden(PromptChatApiError):
    """The LLMClient requires authentication, and the client didn't provide it."""

    status = HTTPStatus.FORBIDDEN.value


class PromptChatApiErrorNotReady(PromptChatApiError):
    """The LLMClient exists, but can't be initialized."""

    status = HTTPStatus.BAD_REQUEST.value


class PromptChatApiErrorLLMProvider(PromptChatApiError):
    """The LLM provider rejected the prompt."""


class PromptChatApiErrorInternal(PromptChatApiError):
    """An unexpected error.

    Its details are logged, never returned.
    """


def requested_contract(request: Optional[HttpRequest]) -> int:
    """
    The version of the contract that the client receives.

    :param request: The configuration or prompt api's request.
    :type request: Optional[django.http.HttpRequest]
    :returns: :data:`~.const.CHAT_CONTRACT_V2`, the default, unless the ``X-Smarter-Capabilities``
        header lists ``chat-contract-v1`` (and not ``chat-contract-v2``), or the client is a version of
        Smarter Chat that lists no contract capability, which reads version 1 only.
    :rtype: int
    """
    if request is None:
        return DEFAULT_CHAT_CONTRACT
    capabilities = str(request.META.get(CAPABILITIES_HEADER, "") or "")
    requested = {capability.strip().lower() for capability in capabilities.split(",")}
    if CHAT_CONTRACT_V2_CAPABILITY in requested:
        return CHAT_CONTRACT_V2
    if CHAT_CONTRACT_V1_CAPABILITY in requested:
        return CHAT_CONTRACT_V1
    if str(request.META.get(CLIENT_HEADER, "") or "").strip().lower() == LEGACY_CHAT_CLIENT:
        return CHAT_CONTRACT_V1
    return DEFAULT_CHAT_CONTRACT


def chat_error_response(
    request: HttpRequest,
    error: PromptChatApiError,
    thing: SmarterJournalThings,
    command: SmarterJournalCliCommands,
) -> SmarterJournaledJsonErrorResponse:
    """
    The error response of the configuration and prompt apis.

    It is a :class:`~.models.PromptChatApiErrorResponse`, the same shape in both versions of the
    contract, without a stack trace.

    :param request: The api's request.
    :type request: django.http.HttpRequest
    :param error: The error, whose class name, message and status the response describes.
    :type error: PromptChatApiError
    :param thing: The journal's thing.
    :type thing: SmarterJournalThings
    :param command: The journal's command.
    :type command: SmarterJournalCliCommands
    :returns: The error response.
    :rtype: SmarterJournaledJsonErrorResponse
    """
    return SmarterJournaledJsonErrorResponse(
        request=request,
        e=error,
        thing=thing,
        command=command,
        description=error.message,
        status=error.status,
        include_stack_trace=False,
    )


def _parse_body(response: dict[str, Any]) -> Optional[dict[str, Any]]:
    """The parsed ``body`` of a prompt's Lambda style result, or None."""
    body = response.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError:
            return None
    return body if isinstance(body, dict) else None


def _completion_without_diagnostics(completion: Any) -> Any:
    """A completion without its ``metadata``, nor the diagnostic keys of its ``smarter`` object."""
    if not isinstance(completion, dict):
        return completion
    completion = {key: value for key, value in completion.items() if key not in DIAGNOSTIC_COMPLETION_TOP_KEYS}
    if not isinstance(completion.get(SMARTER_KEY), dict):
        return completion
    smarter = {key: value for key, value in completion[SMARTER_KEY].items() if key not in DIAGNOSTIC_COMPLETION_KEYS}
    return {**completion, SMARTER_KEY: smarter}


def without_diagnostics(response: Any) -> Any:
    """
    A prompt's result without the complete requests to and responses from the LLM.

    The provider adds them to the completion's ``smarter`` object, as
    :data:`~.const.DIAGNOSTIC_COMPLETION_KEYS`, for the ``smarter`` cli. They include the system
    prompt and every tool result, so a browser never receives them. Nor does it receive the
    completion's ``metadata`` (:data:`~.const.DIAGNOSTIC_COMPLETION_TOP_KEYS`), whose tool calls
    describe each plugin with its owner's profile.

    :param response: A prompt's Lambda style result, as the provider's handler returns it.
    :type response: Any
    :returns: The result, with its body re-serialized without the diagnostic keys. Anything that
        isn't a Lambda style result is returned as is.
    :rtype: Any
    """
    if not isinstance(response, dict):
        return response
    body = _parse_body(response)
    if body is None:
        return response
    if isinstance(body.get("error"), dict) and "response" in body:
        body = {**body, "response": _completion_without_diagnostics(body["response"])}
    else:
        body = _completion_without_diagnostics(body)
    return {**response, "body": json.dumps(body)}


def prompt_result_v2(response: Any) -> tuple[dict[str, Any], Optional[dict[str, Any]], int]:
    """
    A prompt's result, in version 2 of the contract.

    :param response: A prompt's Lambda style result, as the provider's handler returns it.
    :type response: Any
    :returns: The response's ``data`` (a :class:`~.models.PromptChatApiPromptResult`), its ``error`` (a
        :class:`~.models.PromptChatApiErrorBody`, or None if the prompt succeeded), and its http status.
    :rtype: tuple[dict[str, Any], Optional[dict[str, Any]], int]
    """
    response = response if isinstance(response, dict) else {}
    status = int(response.get("statusCode") or HTTPStatus.OK.value)
    body = _parse_body(response) or {}
    provider_error = body.get("error") if isinstance(body.get("error"), dict) else None
    completion = body.get("response") if provider_error else body
    completion = _completion_without_diagnostics(completion) if isinstance(completion, dict) else {}
    smarter = completion.get(SMARTER_KEY) if isinstance(completion.get(SMARTER_KEY), dict) else {}

    error: Optional[dict[str, Any]] = None
    if provider_error or status != HTTPStatus.OK.value:
        description = str((provider_error or {}).get("message") or f"The prompt failed with http status {status}.")
        error = PromptChatApiErrorBody(
            errorClass=PromptChatApiErrorLLMProvider.__name__, description=description, status=status
        ).model_dump()

    result = PromptChatApiPromptResult(
        status=status,
        messages=smarter.get("messages") or [],
        completion=PromptChatApiCompletion.model_validate(completion) if completion else None,
        plugins=smarter.get("plugins") or [],
        tools=smarter.get("tools") or [],
    )
    return result.model_dump(mode="json"), error, status


__all__ = [
    "PromptChatApiError",
    "PromptChatApiErrorForbidden",
    "PromptChatApiErrorInternal",
    "PromptChatApiErrorLLMProvider",
    "PromptChatApiErrorNotFound",
    "PromptChatApiErrorNotReady",
    "chat_error_response",
    "prompt_result_v2",
    "requested_contract",
    "without_diagnostics",
]
