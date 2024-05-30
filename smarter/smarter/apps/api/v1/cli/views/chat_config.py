# pylint: disable=W0613
"""Smarter API command-line interface 'chat' config view"""

import json
import logging

from django.core.cache import cache
from django.http import HttpRequest

from smarter.apps.chatapp.views import ChatConfigView

from .base import APIV1CLIViewError, CliBaseApiView


CACHE_EXPIRATION = 24 * 60 * 60  # 24 hours
SESSION_KEY = "session_key"

logger = logging.getLogger(__name__)


class ApiV1CliChatConfigApiView(CliBaseApiView):
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

    _session_key: str = None
    _data: dict = None

    @property
    def session_key(self) -> str:
        return self._session_key

    @property
    def data(self) -> dict:
        return self._data

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Dispatch method for the ChatConfigView. This method will attempt to
        extract the session_key from the request body. If the session_key is
        not provided then it will attempt to retrieve it from the cache. If
        the session_key is retrieved from the cache then it will be added to
        the request body and passed along to the ChatConfigView.
        """
        name = kwargs.get("name")
        uid = self.params.get("uid")
        self.cache_key = (self.__class__.__name__, name, uid)
        try:
            # extract the session_key from the request body
            # if it exists.
            self._data = json.loads(request.body)
            self._session_key = self.data.get(SESSION_KEY)
        except json.JSONDecodeError:
            pass

        # if the session_key is not provided (our expected case),
        # then attempt to retrieve it from the cache. if we get a hit
        # then we will update the request body with the session_key
        # and pass it along to the ChatConfigView.
        if not self.session_key:
            self._session_key = cache.get(self.cache_key)
            if self.session_key:
                if self.data:
                    new_body = self.data.copy()
                    new_body[SESSION_KEY] = self.session_key
                    new_body = json.dumps(new_body)
                else:
                    new_body = json.dumps({SESSION_KEY: self.session_key})

                # pylint: disable=W0212
                request._body = new_body.encode("utf-8")

        return super().dispatch(request, *args, **kwargs)

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
            session_key = content.get(SESSION_KEY)
            cache.set(key=self.cache_key, value=session_key, timeout=CACHE_EXPIRATION)
        except json.JSONDecodeError as e:
            raise APIV1CLIViewError("Misconfigured. Failed to cache session key for chat config view.") from e

        return response
