# pylint: disable=W0613
"""Smarter API command-line interface 'chat' view"""

import json

from django.core.cache import cache
from django.http import HttpRequest

from .base import CliBaseApiView


CACHE_EXPIRATION = 24 * 60 * 60  # 24 hours
SESSION_KEY = "session_key"


class ApiV1CliChatApiView(CliBaseApiView):
    """Smarter API command-line interface 'chat' view"""

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

    def post(self, request, *args, **kwargs):
        print("ApiV1CliChatApiView.post kwargs:", kwargs)
        return self.broker.chat(request=request, kwargs=kwargs)
