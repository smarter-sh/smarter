# pylint: disable=W0613
"""
This module contains passthrough views for interacting directly with the LLM
provider backend API.
"""

import logging
from http import HTTPStatus

from rest_framework.request import Request

from smarter.apps.account.models import UserProfile
from smarter.apps.provider.services.text_completion.base_classes.protocols import (
    OpenAICompatibleChatCompletionRequest,
    OpenAICompatiblePassthroughProtocol,
)
from smarter.apps.provider.services.text_completion.providers import (
    openai_compatible_passthrough_chat_providers,
)
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
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


class PassthroughChatViewSet(SmarterAuthenticatedAPIView):
    """
    Handle POST requests to the passthrough endpoint for direct LLM provider API access.

    path: /api/v1/prompt/chat/passthrough/{provider_name}/

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

    .. seealso::

        - The OpenAI API documentation for chat completions: https://platform.openai.com/docs/api-reference/chat/create
        - :class:`openai.types.chat.chat_completion.ChatCompletion`
    """

    provider_name: str
    handler: OpenAICompatiblePassthroughProtocol

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.provider_name = self.kwargs.pop("provider_name")
        try:
            self.handler = openai_compatible_passthrough_chat_providers.get_handler(self.provider_name)
        except KeyError:
            return SmarterHttpResponseNotFound(
                request=request, error_message=f"Provider '{self.provider_name}' not found"
            )

    def get(self, request: Request, *args, **kwargs):
        return SmarterHttpResponseBadRequest(
            request=request, error_message="PUT method not supported for passthrough endpoint"
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
        """
        Handle POST requests to the passthrough endpoint for direct LLM
        provider API access.
        """

        # do we know who this is?
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return SmarterHttpResponseForbidden(request=request, error_message="User profile not found")

        # validate the request body to ensure that it conforms to the expected
        # schema for an OpenAI-compatible chat completion request.
        try:
            data = OpenAICompatibleChatCompletionRequest(**request.data)
        except (TypeError, ValueError) as e:
            return SmarterHttpResponseBadRequest(request=request, error_message=str(e))
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Unexpected error parsing request data: %s", e)
            return SmarterHttpResponseServerError(request=request, error_message="Invalid request data format")

        # process the request using the appropriate handler for the specified provider.
        try:
            retval = self.handler(request, user_profile, data, *args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error processing passthrough chat request: %s", e)
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                error_message=str(e),
                command=SmarterJournalCliCommands.CHAT,
                thing=SmarterJournalThings.CHAT,
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        # return a journaled JSON response containing the result from the
        # provider, or an error if something went wrong.
        return SmarterJournaledJsonResponse(
            request=request,
            data=retval,
            command=SmarterJournalCliCommands.CHAT,
            thing=SmarterJournalThings.CHAT,
            status=HTTPStatus.OK,
        )
