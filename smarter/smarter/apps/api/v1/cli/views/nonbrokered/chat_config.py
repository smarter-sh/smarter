# pylint: disable=W0613
"""Smarter API command-line interface 'chat' config view"""

import json
import logging

from django.core.cache import cache
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt

from smarter.apps.chatapp.views import ChatConfigView
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys

from ..base import APIV1CLIViewError
from .chat import CACHE_EXPIRATION, ApiV1CliChatBaseApiView


logger = logging.getLogger(__name__)


class ApiV1CliChatConfigApiView(ApiV1CliChatBaseApiView):
    """
    Smarter API command-line interface 'chat' config view. Returns
    the configuration dict used to configure the React chat component.

    This is a passthrough view that generates its response via ChatConfigView.
    ChatConfigView.post() is called with an optional session_key added to the
    json request body. If the session_key is provided then it is used to
    generate the response. If the session_key is not provided then ChatConfigView
    will generate a new session_key and return it in the response.

    In either case, the session_key that is returned will be cached for 24 hours
    using the cache_key property. Note that reused session_keys will be recached
    indefinitely.

    The cache_key is a combination of the class name, the chat name and a client
    UID created from the machine mac address and its hostname.

    See smarter/apps/chatapp/data/chat_config.json for an example response to
    this request.
    """

    def setup(self, request: HttpRequest, *args, **kwargs):
        """
        Setup the view. This is called before dispatch() and is used to
        set up the view for the request.
        """
        super().setup(request, *args, **kwargs)
        self._is_config_view = False
        logger.info("ApiV1CliChatConfigApiView.setup() - %s", self.formatted_class_name)

    @csrf_exempt
    def post(self, request: HttpRequest, name: str, *args, **kwargs):
        """
        Api v1 post method for chat config view. Returns the configuration
        dict used to configure the React chat component.

        :param request: Request object
        :param name: Name of the chat
        :param uid: UID of the client, created from the machine mac address and the hostname
        """
        uid: str = request.POST.get("uid", None)
        logger.info("%s Chat config view for chat %s and client %s.", self.formatted_class_name, name, uid)

        response = ChatConfigView.as_view()(request, name=name)

        try:
            content = json.loads(response.content)
            content = content.get(SmarterJournalApiResponseKeys.DATA)
            session_key = content.get(SMARTER_CHAT_SESSION_KEY_NAME)
            cache.set(key=self.cache_key, value=session_key, timeout=CACHE_EXPIRATION)
        except json.JSONDecodeError as e:
            raise APIV1CLIViewError("Misconfigured. Failed to cache session key for chat config view.") from e

        return response
