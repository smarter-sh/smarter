"""
This module contains passthrough views for interacting directly with the LLM
provider backend API.
"""

import logging
from typing import Optional

import openai
from openai.types.chat.chat_completion import ChatCompletion
from rest_framework.request import Request

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
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from . import ChatDbMixin


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class OpenAICompatiblePassthroughChatProvider(ChatDbMixin):
    """
    A passthrough chat provider that is fully compatible with OpenAI's API. This
    provider allows authenticated users to send arbitrary OpenAI-compatible
    prompt dicts directly to the underlying API. It handles authentication,
    request forwarding, and response handling.

    Smarter-specific features include:

    - Emits signals for chat lifecycle events
    - Logs interactions based on a waffle switch.
    - Returns journaled JSON responses for integration with Smarter's journaling system.
    - Manages history and charge records asynchronously via ChatDbMixin

                provider=PROVIDER_NAME,
            base_url=BASE_URL,
            api_key=smarter_settings.gemini_api_key.get_secret_value(),

    """

    def __init__(self, *args, provider: str, base_url: str, api_key: str, **kwargs):
        super().__init__(*args, **kwargs)

        self.provider = provider.lower()
        self.base_url = base_url
        self.api_key = api_key

    def handler(self, request: Request, *args, **kwargs):
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
