# pylint: disable=W0613
"""
This module contains passthrough views for interacting directly with the LLM
provider backend API.
"""

import logging
from typing import Optional

import openai
from openai.types.chat.chat_completion import ChatCompletion
from rest_framework.request import Request

from smarter.apps.prompt.providers.base_classes import ChatDbMixin
from smarter.apps.prompt.signals import (
    chat_completion_request,
    chat_completion_response,
    chat_finished,
    chat_response_failure,
    chat_started,
)
from smarter.apps.provider.models import Provider
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class PromptPassthroughView(SmarterAuthenticatedAPIView):
    """
    Handle POST requests to the passthrough endpoint for direct LLM provider API access.

    This endpoint allows authenticated users to send arbitrary prompt dicts
    to the underlying LLM provider (such as OpenAI). The request body should
    be a JSON object containing any valid parameters accepted by the
    provider's chat completion API.

    :param request: The HTTP request object, expected to have a JSON body with chat completion parameters.
    :type request: rest_framework.request.Request
    :param args: Additional positional arguments (unused).
    :param kwargs: Additional keyword arguments. May include 'provider' to select the LLM provider.
    :return: A JSON response containing the provider's chat completion result, or an error message.
    :rtype: SmarterJournaledJsonResponse | SmarterJournaledJsonErrorResponse | SmarterHttpResponseBadRequest | SmarterHttpResponseForbidden | SmarterHttpResponseNotFound

    :signals:
        - ``chat_started``: Sent before the chat completion request is made.
        - ``chat_completion_request``: Sent with the prompt data before calling the provider.
        - ``chat_completion_response``: Sent after a successful response from the provider.
        - ``chat_finished``: Sent after the chat completion process is finished.
        - ``chat_response_failure``: Sent if an exception occurs during the provider call.

    :raises SmarterHttpResponseForbidden: If the user is not authenticated.
    :raises SmarterHttpResponseNotFound: If the specified provider is not found.
    :raises SmarterHttpResponseBadRequest: If the request body is invalid.
    :raises SmarterJournaledJsonErrorResponse: If the provider API call fails.

    **Valid request body keys include (but are not limited to):**

        - messages: Iterable[ChatCompletionMessageParam]
        - model: Union[str, ChatModel]
        - audio: Optional[ChatCompletionAudioParam]
        - frequency_penalty: Optional[float]
        - function_call: completion_create_params.FunctionCall
        - functions: Iterable[completion_create_params.Function]
        - logit_bias: Optional[Dict[str, int]]
        - logprobs: Optional[bool]
        - max_completion_tokens: Optional[int]
        - max_tokens: Optional[int]
        - metadata: Optional[Metadata]
        - modalities: Optional[List[Literal["text", "audio"]]]
        - n: Optional[int]
        - parallel_tool_calls: bool
        - prediction: Optional[ChatCompletionPredictionContentParam]
        - presence_penalty: Optional[float]
        - prompt_cache_key: str
        - prompt_cache_retention: Optional[Literal["in-memory", "24h"]]
        - reasoning_effort: Optional[ReasoningEffort]
        - response_format: completion_create_params.ResponseFormat
        - safety_identifier: str
        - seed: Optional[int]
        - service_tier: Optional[Literal["auto", "default", "flex", "scale", "priority"]]
        - stop: Union[Optional[str], SequenceNotStr[str], None]
        - store: Optional[bool]
        - stream: Optional[Literal[False]]
        - stream_options: Optional[ChatCompletionStreamOptionsParam]
        - temperature: Optional[float]
        - tool_choice: ChatCompletionToolChoiceOptionParam
        - tools: Iterable[ChatCompletionToolUnionParam]
        - top_logprobs: Optional[int]
        - top_p: Optional[float]
        - user: str
        - verbosity: Optional[Literal["low", "medium", "high"]]
        - web_search_options: completion_create_params.WebSearchOptions
        - extra_headers: Headers | None
        - extra_query: Query | None
        - extra_body: Body | None
        - timeout: float | httpx.Timeout | None | NotGiven
    """

    def get(self, request: Request, *args, **kwargs):
        return SmarterHttpResponseBadRequest(
            request=request, error_message="GET method not supported for passthrough endpoint"
        )

    def put(self, request: Request, *args, **kwargs):
        return SmarterHttpResponseBadRequest(
            request=request, error_message="PUT method not supported for passthrough endpoint"
        )

    def delete(self, request: Request, *args, **kwargs):
        return SmarterHttpResponseBadRequest(
            request=request, error_message="DELETE method not supported for passthrough endpoint"
        )

    def patch(self, request: Request, *args, **kwargs):
        return SmarterHttpResponseBadRequest(
            request=request, error_message="PATCH method not supported for passthrough endpoint"
        )

    def options(self, request: Request, *args, **kwargs):
        return SmarterHttpResponseBadRequest(
            request=request, error_message="OPTIONS method not supported for passthrough endpoint"
        )

    def post(self, request: Request, *args, **kwargs):
        response: Optional[ChatCompletion] = None
        provider: Optional[Provider] = None
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return SmarterHttpResponseForbidden(
                request=request, error_message="Authentication required to use passthrough endpoint"
            )

        logger.info("%s.post() called with data: %s", self.formatted_class_name, request.data)

        provider_name = kwargs.pop("provider", None)
        try:
            provider = Provider.get_cached_object(name=provider_name, user=request.user)  # type: ignore
            if not provider:
                raise Provider.DoesNotExist
            logger.debug("%s.post() using provider: %s", self.formatted_class_name, provider)
        except Provider.DoesNotExist:
            return SmarterHttpResponseNotFound(request=request, error_message="Provider not found")

        chat_db_mixin = ChatDbMixin()

        if provider.api_key:
            openai.api_key = provider.api_key.get_secret_value()
        openai.base_url = provider.base_url

        if not hasattr(request, "data") or not isinstance(request.data, dict):
            return SmarterHttpResponseBadRequest(
                request=request, error_message="Invalid request body: expected a JSON object"
            )
        data = request.data

        chat_started.send(sender=self.__class__, request=request)
        chat_completion_request.send(sender=self.__class__, request=request, prompt=data)

        try:
            response = openai.chat.completions.create(**data)
        # pylint: disable=broad-except
        except Exception as e:
            # send error signal
            response = None
            chat_response_failure.send(sender=self.__class__, request=request, error=e)
            logger.error("Error calling OpenAI API: %s", str(e), exc_info=True)
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                thing=SmarterJournalThings.CHAT,
                command=SmarterJournalCliCommands.CHAT,
            )

        chat_completion_response.send(sender=self.__class__, request=request, response=response)
        chat_finished.send(sender=self.__class__, request=request, response=response)

        response_dict: dict = {"message": "Response is not a ChatCompletion object"}
        if isinstance(response, ChatCompletion):
            response_dict = response.model_dump()

        logger.debug("%s.post() returning response: %s", self.formatted_class_name, response_dict)
        return SmarterJournaledJsonResponse(
            request=request, data=response_dict, thing=SmarterJournalThings.CHAT, command=SmarterJournalCliCommands.CHAT
        )
