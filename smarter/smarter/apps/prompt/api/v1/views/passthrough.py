# pylint: disable=W0613
"""
This module contains passthrough views for interacting directly with the LLM
provider backend API.
"""

import logging
from http import HTTPStatus

from openai.types.chat.chat_completion import ChatCompletion
from rest_framework.request import Request

from smarter.apps.account.models import UserProfile
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.lib.protocols import (
    OpenAICompatiblePassthroughProtocol,
)
from smarter.apps.provider.services.text_completion.providers import (
    openai_compatible_client,
)
from smarter.common.exceptions import SmarterIlligalInvocationError
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpErrorResponse,
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


class PassthroughChatViewSet(SmarterAuthenticatedAPIView):
    """
    Handle POST requests to the passthrough endpoint for direct LLM provider API access.

    path: /api/v1/prompts/passthrough/{provider_name}/

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

    .. seealso::

        - The OpenAI API documentation for chat completions: https://platform.openai.com/docs/api-reference/chat/create
        - :class:`openai.types.chat.chat_completion.ChatCompletion`
    """

    provider_name: str
    handler: OpenAICompatiblePassthroughProtocol

    def setup(self, request, *args, **kwargs):
        """
        Set the provider_name and handler based on the URL kwargs.
        The handler can be any function that implements the
        :class:`OpenAICompatiblePassthroughProtocol` interface.

        .. seealso::

            - :class:`OpenAICompatiblePassthroughProtocol`
        """
        self.provider_name = kwargs.pop("provider_name")
        super().setup(request, *args, **kwargs)
        try:
            self.handler = openai_compatible_client.get_passthrough_handler(request, self.provider_name)
        except (KeyError, Provider.DoesNotExist):
            logger.error("Provider '%s' not found in openai_compatible_client", self.provider_name)
            return SmarterHttpResponseNotFound(
                error_message=f"Provider '{self.provider_name}' not found", request=request
            )
        logger.debug(
            "%s.setup() provider_name: %s and handler: %s", self.formatted_class_name, self.provider_name, self.handler
        )

    def get(self, request: Request, *args, **kwargs) -> SmarterHttpResponseBadRequest:
        return SmarterHttpResponseBadRequest(
            request=request, error_message="GET method not supported for passthrough endpoint"
        )

    def put(self, request: Request, *args, **kwargs) -> SmarterHttpResponseBadRequest:
        return SmarterHttpResponseBadRequest(
            request=request, error_message="PUT method not supported for passthrough endpoint"
        )

    def delete(self, request: Request, *args, **kwargs) -> SmarterHttpResponseBadRequest:
        return SmarterHttpResponseBadRequest(
            request=request, error_message="DELETE method not supported for passthrough endpoint"
        )

    def patch(self, request: Request, *args, **kwargs) -> SmarterHttpResponseBadRequest:
        return SmarterHttpResponseBadRequest(
            request=request, error_message="PATCH method not supported for passthrough endpoint"
        )

    def options(self, request: Request, *args, **kwargs) -> SmarterHttpResponseBadRequest:
        return SmarterHttpResponseBadRequest(
            request=request, error_message="OPTIONS method not supported for passthrough endpoint"
        )

    def post(
        self, request: Request, *args, **kwargs
    ) -> (
        SmarterJournaledJsonResponse
        | SmarterJournaledJsonErrorResponse
        | SmarterHttpErrorResponse
        | SmarterHttpResponseForbidden
    ):
        """
        Handle POST requests to the passthrough endpoint for direct LLM
        provider API access.
        """
        logger_prefix = formatted_text(f"{__name__}.{self.formatted_class_name}.post()")
        kwargs.pop("provider_name")
        logger.debug("%s called with args: %s, kwargs: %s", logger_prefix, args, kwargs)

        # do we know who this is?
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            logger.debug("%s verified user_profile: %s", logger_prefix, user_profile)
        except UserProfile.DoesNotExist:
            return SmarterHttpResponseForbidden(request=request, error_message="User profile not found")

        # process the request using the appropriate handler for the specified provider.
        try:
            logger.debug(
                "%s calling handler: %s with data: %s",
                logger_prefix,
                self.handler,
                formatted_json(request.data),
            )
            retval = self.handler(request, user_profile, request.data, *args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s Error processing request: %s", logger_prefix, e)
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                error_message=str(e),
                command=SmarterJournalCliCommands.CHAT,
                thing=SmarterJournalThings.CHAT,
                status=HTTPStatus.BAD_REQUEST,
            )

        # this is our hoped-for case. The handler should return a ChatCompletion
        # Pydantic model which we can directly serialize and return to the client.
        if isinstance(retval, ChatCompletion):
            logger.debug("%s received ChatCompletion response: %s", logger_prefix, formatted_json(retval.model_dump()))
            return SmarterJournaledJsonResponse(
                request=request,
                data=retval.model_dump(),
                command=SmarterJournalCliCommands.CHAT,
                thing=SmarterJournalThings.CHAT,
                status=HTTPStatus.OK,
            )

        # catch the various ways that things could have gone wrong. Ideally this
        # will only otherwise return an instance of SmarterJournaledJsonResponse,
        # but we'll be defensive here and catch any SmarterHttpErrorResponse as well.
        if isinstance(retval, (SmarterHttpErrorResponse, SmarterJournaledJsonResponse)):
            return retval

        # if we got here then something has gone terribly wrong.
        raise SmarterIlligalInvocationError(
            f"Unexpected return type from handler: {type(retval)}. Expected ChatCompletion or SmarterHttpErrorResponse."
        )
