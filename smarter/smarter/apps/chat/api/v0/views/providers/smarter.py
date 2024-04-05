# -*- coding: utf-8 -*-
# pylint: disable=R0801
"""Customer API views."""

import logging
from http import HTTPStatus

from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from smarter.apps.account.api.view_helpers import SmarterAPIView
from smarter.apps.chat.providers.smarter import handler
from smarter.apps.chatbot.models import ChatBot
from smarter.common.utils import exception_response_factory, http_response_factory


logger = logging.getLogger(__name__)


class SmarterChatViewSet(SmarterAPIView):
    """top-level viewset for openai api function calling"""

    def post(self, request):
        """
        POST request handler for the Smarter Chat API. We need to parse the request host
        to determine which ChatBot instance to use. There are two possible hostname formats:

        URL with default api domain
        -------------------
        example: https://customer-support.5416-2700-9825.api.smarter.sh/chatbot/
        where
         - `customer-service' == chatbot.name`
         - `5416-2700-9825 == chatbot.account.account_number`
         - `api.smarter.sh == smarter_settings.customer_api_domain`

        URL with custom domain
        -------------------
        example: https://api.smarter.querium.com/chatbot/
        where
         - `api.smarter.querium.com == chatbot.custom_domain`
         - `ChatBotCustomDomain.is_verified == True` noting that
           an asynchronous task has verified the domain NS records.

        The ChatBot instance hostname is determined by the following logic:
        `chatbot.hostname == chatbot.custom_domain or chatbot.default_host`
        """
        chatbot: ChatBot = None

        try:
            chatbot = ChatBot.objects.get(hostname=request.get_host())
        except ChatBot.DoesNotExist as e:
            return http_response_factory(
                status_code=HTTPStatus.NOT_FOUND,
                body=exception_response_factory(e),
            )

        # FIX NOTE: this might be an unnecessary belt & suspenders step. DRF might be already
        # doing all of this for us.
        response = Response(handler(chatbot=chatbot, user=request.user, data=request.data))
        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = "application/json"
        response.renderer_context = {}
        return response
