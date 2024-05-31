# pylint: disable=W0613
"""Smarter API command-line interface 'chat' config view"""

import json
import logging

from django.core.cache import cache
from django.http import HttpRequest

from smarter.apps.chatapp.views import ChatConfigView
from smarter.lib.manifest.enum import SCLIResponseGet

from .base import APIV1CLIViewError
from .chat import CACHE_EXPIRATION, SESSION_KEY, ApiV1CliChatBaseApiView


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
    """

    def post(self, request: HttpRequest, name: str, uid: str, *args, **kwargs):
        """
        Api v1 post method for chat config view. Returns the configuration
        dict used to configure the React chat component.

        :param request: Request object
        :param name: Name of the chat
        :param uid: UID of the client, created from the machine mac address and the hostname
        """
        response = ChatConfigView.as_view()(request, name=name)

        try:
            content = json.loads(response.content)
            content = content.get(SCLIResponseGet.DATA)
            session_key = content.get(SESSION_KEY)
            cache.set(key=self.cache_key, value=session_key, timeout=CACHE_EXPIRATION)
        except json.JSONDecodeError as e:
            raise APIV1CLIViewError("Misconfigured. Failed to cache session key for chat config view.") from e

        return response
