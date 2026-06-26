# pylint: disable=W0613
"""
This module contains passthrough views for interacting directly with the LLM.

provider backend API.
"""

import logging
from http import HTTPStatus
from typing import Any

from django.core.handlers.asgi import ASGIRequest
from openai.types.chat.chat_completion import ChatCompletion

from smarter.apps.account.models import UserProfile, charge_authorization
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.lib.protocols import (
    OpenAICompatiblePassthroughProtocol,
)
from smarter.apps.provider.services.text_completion.providers import (
    openai_compatible_client,
)
from smarter.common.exceptions import SmarterIlligalInvocationError
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpErrorResponse,
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
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


class PassthroughChatViewSet(SmarterAuthenticatedNeverCachedWebView):
    """
    Handle POST requests to the passthrough endpoint for direct LLM provider API access.

    path: /api/v1/prompts/passthrough/{provider_name}/

    This endpoint allows authenticated users to send arbitrary prompt dicts
    to the underlying LLM provider (such as OpenAI). The request body should
    be a JSON object containing any valid parameters accepted by the
    provider's prompt completion API.

    :param request: The HTTP request object, expected to have a JSON body with prompt completion parameters.
    :type request: rest_framework.request.ASGIRequest
    :param args: Additional positional arguments (unused).
    :param kwargs: Additional keyword arguments. May include 'provider' to select the LLM provider.
    :return: A JSON response containing the provider's prompt completion result, or an error message.
    :rtype: SmarterJournaledJsonResponse | SmarterJournaledJsonErrorResponse | SmarterHttpResponseBadRequest | SmarterHttpResponseForbidden | SmarterHttpResponseNotFound

    :signals:
        - ``prompt_started``: Sent before the prompt completion request is made.
        - ``chat_request``: Sent with the prompt data before calling the provider.
        - ``chat_response``: Sent after a successful response from the provider.
        - ``prompt_finished``: Sent after the prompt completion process is finished.
        - ``chat_response_failure``: Sent if an exception occurs during the provider call.

    :raises SmarterHttpResponseForbidden: If the user is not authenticated.
    :raises SmarterHttpResponseNotFound: If the specified provider is not found.
    :raises SmarterHttpResponseBadRequest: If the request body is invalid.
    :raises SmarterJournaledJsonErrorResponse: If the provider API call fails.

    .. seealso::

        - The OpenAI API documentation for prompt completions: https://developers.openai.com/api/reference/overview/prompt/create
        - :class:`openai.types.prompt.chat_completion.ChatCompletion`
    """

    provider_name: str
    handler: OpenAICompatiblePassthroughProtocol

    def setup(self, request: ASGIRequest, *args, **kwargs):
        """
        Set the provider_name and handler based on the URL kwargs.

        The handler can be any function that implements the
        :class:`OpenAICompatiblePassthroughProtocol` interface.

        .. seealso::

            - :class:`OpenAICompatiblePassthroughProtocol`
        """
        provider_name = kwargs.pop("provider_name")
        provider_name = self.to_snake_case(provider_name)
        self.provider_name = provider_name
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

    def post(
        self, request: ASGIRequest, *args, **kwargs
    ) -> (
        SmarterJournaledJsonResponse
        | SmarterJournaledJsonErrorResponse
        | SmarterHttpErrorResponse
        | SmarterHttpResponseForbidden
    ):
        """
        Handle POST requests to the passthrough endpoint for direct LLM.

        provider API access.
        """
        charge_authorization(self.user_profile.record_locator, self.__class__.__name__)  # type: ignore
        logger_prefix = formatted_text(f"{__name__}.{self.formatted_class_name}.post()")
        kwargs.pop("provider_name")
        logger.debug("%s called with request: %s, args: %s, kwargs: %s", logger_prefix, request, args, kwargs)

        # do we know who this is?
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            logger.debug("%s verified user_profile: %s", logger_prefix, user_profile)
        except UserProfile.DoesNotExist:
            return SmarterHttpResponseForbidden(request=request, error_message="User profile not found")
        except UserProfile.MultipleObjectsReturned:
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if not user_profile:
                return SmarterHttpResponseForbidden(request=request, error_message="User profile not found")
            logger.warning(
                "%s Multiple user profiles found for user: %s. Arbitrarily selecting the first one: %s",
                logger_prefix,
                request.user,
                user_profile,
            )

        try:
            data: dict[str, Any] = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("%s JSON decode error: %s. Raw request body: %s", logger_prefix, e, request.body)
            return SmarterHttpResponseBadRequest(request=request, error_message="Invalid JSON body")

        # process the request using the appropriate handler for the specified provider.
        try:
            logger.debug(
                "%s calling handler: %s with data: %s",
                logger_prefix,
                self.handler,
                formatted_json(data),
            )
            retval = self.handler(request, user_profile, data, *args, **kwargs)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s Error processing request: %s", logger_prefix, e)
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                error_message=str(e),
                command=SmarterJournalCliCommands.PROMPT,
                thing=SmarterJournalThings.PROMPT,
                status=HTTPStatus.BAD_REQUEST,
            )

        # this is our hoped-for case. The handler should return a ChatCompletion
        # Pydantic model which we can directly serialize and return to the client.
        if isinstance(retval, ChatCompletion):
            logger.debug("%s received ChatCompletion response: %s", logger_prefix, formatted_json(retval.model_dump()))
            return SmarterJournaledJsonResponse(
                request=request,
                data=retval.model_dump(),
                command=SmarterJournalCliCommands.PROMPT,
                thing=SmarterJournalThings.PROMPT,
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
