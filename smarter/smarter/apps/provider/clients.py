"""
This module contains passthrough views for interacting directly with the LLM
provider backend API.
"""

import logging
import traceback
from http import HTTPStatus
from typing import Any, Optional

import openai
from openai.types.chat.chat_completion import ChatCompletion
from rest_framework.request import Request

from smarter.apps.account.models.user_profile import UserProfile
from smarter.apps.prompt.signals import (
    chat_completion_request,
    chat_completion_response,
    chat_finished,
    chat_response_failure,
    chat_started,
)
from smarter.apps.provider.models import Provider
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
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


class SmarterOpenAIClient(SmarterHelperMixin):
    """
    A passthrough chat provider that is fully compatible with OpenAI's API.
    This provider allows authenticated users to send arbitrary OpenAI-compatible
    prompt dicts directly to the underlying API. It handles authentication,
    request forwarding, and response handling.

    Smarter-specific features include:

    - Emits signals for chat lifecycle events
    - Logs interactions based on a waffle switch
    - Returns journaled JSON responses for integration with Smarter's journaling system
    - Manages history and charge records asynchronously via ChatDbMixin

    Example usage::

        provider=PROVIDER_NAME
        base_url=BASE_URL
        api_key=smarter_settings.gemini_api_key.get_secret_value()

    """

    def __init__(self, *args, provider: str, base_url: str, api_key: str, **kwargs):
        super().__init__(*args, **kwargs)

        self.provider = provider.lower()
        self.base_url = base_url
        self.api_key = api_key

    def handler(
        self,
        request: Request,
        user_profile: UserProfile,
        data: dict[str, Any],
        **kwargs,
    ):
        logger_prefix = formatted_text(f"{__name__}.{self.formatted_class_name}.handler()")
        response: Optional[ChatCompletion] = None
        provider: Optional[Provider] = None
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return SmarterHttpResponseForbidden(
                request=request, error_message="Authentication required to use passthrough endpoint"
            )

        logger.debug(
            "%s called with request: %s, user_profile: %s, api_key: %s, base_url: %s, provider_name: %s, data: %s",
            logger_prefix,
            request,
            user_profile,
            formatted_json(data),
        )
        try:
            provider = Provider.objects.filter(name=self.provider).with_read_permission_for(request.user).first()  # type: ignore
            if not provider:
                raise Provider.DoesNotExist
            logger.debug("%s found provider: %s", logger_prefix, provider)
            if provider.api_key:
                openai.api_key = provider.api_key.get_secret()
            openai.base_url = provider.base_url
        except Provider.DoesNotExist:
            logger.error("%s provider not found: %s", logger_prefix, self.provider)
            return SmarterHttpResponseNotFound(request=request, error_message="Provider not found")
        if self.api_key:
            openai.api_key = self.api_key
        if self.base_url:
            openai.base_url = self.base_url

        if not hasattr(request, "data") or not isinstance(request.data, dict):
            return SmarterHttpResponseBadRequest(
                request=request, error_message="Invalid request body: expected a JSON object"
            )
        data = request.data

        chat_started.send(sender=self.handler, request=request, data=data)
        chat_completion_request.send(sender=self.handler, data=data)

        try:
            logger.debug("%s sending request to %s with data: %s", logger_prefix, openai.base_url, formatted_json(data))
            response = openai.chat.completions.create(**data)
        # pylint: disable=broad-except
        except Exception as e:
            stack_trace = traceback.format_exc()
            chat_response_failure.send(
                sender=self.handler,
                iteration=1,
                exception=e,
                first_iteration=data,
                messages=data.get("messages") if isinstance(data, dict) else None,
                stack_trace=stack_trace,
            )

            logger.error("%s error calling %s: %s", logger_prefix, openai.base_url, str(e), exc_info=True)
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                thing=SmarterJournalThings.CHAT,
                command=SmarterJournalCliCommands.CHAT,
                status_code=HTTPStatus.BAD_REQUEST,
                error_message=str(e),
                description=str(e),
                stack_trace=stack_trace,
            )

        chat_completion_response.send(sender=self.handler, request=request, response=response)
        chat_finished.send(sender=self.handler, request=request, response=response)

        response_dict: dict = {"message": "Response is not a ChatCompletion object"}
        if isinstance(response, ChatCompletion):
            response_dict = response.model_dump()

        logger.debug("%s returning response: %s", logger_prefix, formatted_json(response_dict))
        return SmarterJournaledJsonResponse(
            request=request, data=response_dict, thing=SmarterJournalThings.CHAT, command=SmarterJournalCliCommands.CHAT
        )
