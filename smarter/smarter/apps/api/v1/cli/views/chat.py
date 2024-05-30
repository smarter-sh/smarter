# pylint: disable=W0613
"""Smarter API command-line interface 'chat' view"""

import hashlib
import json
from typing import Tuple

from django.core.cache import cache
from django.http import HttpRequest

from .base import APIV1CLIViewError, CliBaseApiView


CACHE_EXPIRATION = 24 * 60 * 60  # 24 hours
SESSION_KEY = "session_key"


class APIV1CLIChatViewError(APIV1CLIViewError):
    """APIV1CLIChatViewError exception class"""

    @property
    def get_readable_name(self):
        return "Smarter api v1 cli chat error"


class ApiV1CliChatBaseApiView(CliBaseApiView):
    """Smarter API command-line interface 'chat' view"""

    _cache_key: str = None
    _data: dict = None
    _name: str = None
    _prompt: str = None
    _session_key: str = None

    @property
    def prompt(self) -> str:
        """
        The chat prompt from the request body. This is a single raw text input
        from the user. This will need to be added to a message list and sent
        to the chatbot.
        """
        return self.data.get("prompt", None)

    @property
    def new_session(self) -> bool:
        """True if the new_session url parameter was passed and is set to 'true'"""
        if self.params.get("new_session", "false").lower() not in ["true", "false"]:
            bad_value = self.params.get("new_session")
            raise APIV1CLIChatViewError(
                f"Invalid value '{bad_value}' provided for url param new_session. Must be 'true' or 'false'."
            )
        return str(self.params.get("new_session", "false")).lower() == "true"

    @property
    def uid(self) -> str:
        """
        Unique identifier for the client. This is assumed to be a
        combination of the machine mac address and the hostname.
        """
        return self.params.get("uid", None)

    @property
    def name(self) -> str:
        """The name of the ChatBot. This is passed as a url slug."""
        return self._name

    @property
    def cache_key(self) -> str:
        """For cached values, get the cache key for the chat config view."""
        if not self._cache_key:
            raise APIV1CLIViewError("Internal error. Cache key has not been set.")
        return self._cache_key

    @cache_key.setter
    def cache_key(self, key_tuple: Tuple[str, str, str, str]) -> None:
        """
        Set a cache key based on a name string and a unique identifier 'uid'. This key is used to cache
        the session_key for the chat. The key is a combination of the class name, authenticated username,
        the chat name, and the client UID. Currently used by the
        ApiV1CliChatConfigApiView and ApiV1CliChatApiView as a means of sharing the session_key.

        :param name: a generic object or resource name
        :param uid: UID of the client, assumed to have been created from the
         machine mac address and the hostname of the client
        """
        class_name, username, name, uid = key_tuple
        raw_string = class_name + "_" + username + "_" + name + "_" + uid
        hash_object = hashlib.sha256()
        hash_object.update(raw_string.encode())
        hash_string = hash_object.hexdigest()
        self._cache_key = hash_string

    @property
    def session_key(self) -> str:
        """
        The session_key identifying a chat session for a user/chatbot.
        This is used to persist the chat history of session, so that the
        same chat session can be continued indefinitely.
        """
        return self._session_key

    @property
    def data(self) -> dict:
        """The raw contents of the request body, assumed to be in json format."""
        return self._data or {}

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Base dispatch method for the Chat views. This method will attempt to
        extract the session_key from the request body. If the session_key is
        not provided then it will attempt to retrieve it from the cache. If
        the session_key is retrieved from the cache then it will be added to
        the request body and passed along to the ChatConfigView.

        This view also extracts the prompt from the request body and sets it.

        - cache_key: the cache key is derived from unique identifiers send by the client
          in the form of a url parameter named 'uid'. The cache key is used to cache
          the session_key for Chat.

        - prompt: the prompt is the raw text of the chat message that is sent to the
            chatbot. The prompt is added to the payload of the request body and is
            distinguished from the manifest text based on the url path.

        """
        self._name = kwargs.get("name")

        try:
            # extract the body from the request body
            # if it exists.
            self._data = json.loads(request.body)

            # try to extract the session_key from the request body
            # if it exists.
            self._session_key = self.data.get(SESSION_KEY)
        except json.JSONDecodeError:
            pass

        if not self.uid:
            raise APIV1CLIChatViewError(
                "Internal error. UID is missing. This is intended to be a unique identifier for the client, passed as a url param named 'uid'."
            )

        self.cache_key = (self.__class__.__name__, self.request.user.username, self.name, self.uid)

        # if the new_session url parameter was passed and is set to True
        # then we will delete the cache_key and the session_key.
        if self.new_session:
            self._session_key = None
            cache.delete(self.cache_key)

        # attempt to retrieve a session_key from the cache. if we get a hit
        # then we will update the request body with the session_key
        # and pass it along to the ChatConfigView.
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


class ApiV1CliChatApiView(ApiV1CliChatBaseApiView):
    """
    Smarter API command-line interface 'chat' view. Constructs a chat message list
    and returns the Smarter chat response.

    This is a passthrough view that generates its response via ???????.
    ???????.post() is called with an optional session_key added to the
    json request body. If the session_key is provided then it is used to
    generate the response. If the session_key is not provided then it
    will generate a new session_key and return it in the response.

    In either case, the session_key that is returned will be cached for 24 hours
    using the cache_key property. Note that reused session_keys will be recached
    indefinitely.

    The cache_key is a combination of the class name, the chat name and a client
    UID created from the machine mac address and its hostname.
    """

    def post(self, request, *args, **kwargs):
        print("ApiV1CliChatApiView.post kwargs:", kwargs)
        return self.broker.chat(request=request, kwargs=kwargs)
