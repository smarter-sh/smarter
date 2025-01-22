# pylint: disable=W0613
"""Smarter API command-line interface 'chat' view"""

import hashlib
import json
import logging
from typing import Tuple
from urllib.parse import urlparse

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from smarter.apps.chat.models import Chat, ChatHistory
from smarter.apps.chat.providers.const import OpenAIMessageKeys
from smarter.apps.chatapp.views import ChatConfigView
from smarter.apps.chatbot.api.v1.views.default import DefaultChatBotApiView
from smarter.apps.chatbot.models import ChatBot
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.manifest.enum import SCLIResponseGet

from ..base import APIV1CLIViewError, CliBaseApiView


CACHE_EXPIRATION = 24 * 60 * 60  # 24 hours

logger = logging.getLogger(__name__)


class APIV1CLIChatViewError(APIV1CLIViewError):
    """APIV1CLIChatViewError exception class"""

    @property
    def get_formatted_err_message(self):
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
            self._session_key = self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
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
                new_body[SMARTER_CHAT_SESSION_KEY_NAME] = self.session_key
                new_body = json.dumps(new_body)
            else:
                new_body = json.dumps({SMARTER_CHAT_SESSION_KEY_NAME: self.session_key})

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

    Example kwargs:
    kwargs: {'new_session': ['false'], 'uid': ['Lawrences-Mac-Studio.local-c6%3A6b%3A2e%3A7a%3A3d%3A6c']}

    example request/response:
    - smarter/apps/chatapp/data/chat_config.json
    - smarter/apps/chatapp/data/request.json
    - smarter/apps/chatapp/data/response.json
    """

    _chat_config: dict = None
    _chat_history: ChatHistory = None
    _messages: list[dict] = None

    @property
    def chat_config(self) -> dict:
        """The chat configuration dict."""
        return self._chat_config or {}

    @property
    def chatbot_config(self) -> dict[str, any]:
        """The chatbot configuration dict."""
        return self.chat_config.get("chatbot", {})

    @property
    def url_chatbot(self) -> str:
        """The url of the chatbot."""
        return self.chatbot_config.get("url_chatbot", None)

    @property
    def chat_history(self) -> dict:
        if not self._chat_history:
            try:
                chat = Chat.objects.get(session_key=self.session_key)
            except Chat.DoesNotExist:
                return None
            try:
                self._chat_history = ChatHistory.objects.filter(chat=chat).latest("created_at")
            except ChatHistory.DoesNotExist:
                return None
        return self._chat_history

    @property
    def messages(self) -> list[dict[str, str]]:
        """The message list for the chat."""
        if not self._messages:
            # the cli is forcing a new session, so disregard the chat history
            # and create a new message list that includes the welcome message.
            if self.new_session:
                self._messages = self.new_message_list_factory()
            else:
                # try to get the messages from the chat history, is it exists
                request: dict = self.chat_history.request if self.chat_history else None
                if request:
                    self._messages: list[dict] = request.get("messages", [])
                    self._messages.append({"role": "user", "content": self.prompt})
                # otherwise, create a new message list
                else:
                    self._messages = self.new_message_list_factory()
        return self._messages

    def new_message_list_factory(self) -> list[dict[str, str]]:

        system_role: str = self.chatbot_config.get(
            "default_system_role",
            self.chat_config.get("default_system_role", smarter_settings.llm_default_system_role),
        )
        welcome_message: str = self.chatbot_config.get("app_welcome_message", "[MISSING WELCOME MESSAGE]")
        app_assistant: str = self.chatbot_config.get("app_assistant", "[MISSING ASSISTANT NAME]")
        example_prompts: list[str] = self.chatbot_config.get(
            "app_example_prompts", ["example prompt 1", "example prompt 2", "example prompt 3"]
        )
        bullet_points = "\n".join(f"    - {prompt}" for prompt in example_prompts)
        bullet_points = "Following are some example prompts:\n\n" + bullet_points + "\n\n"
        intro = f"I'm {app_assistant}, how can I assist you today?"
        return [
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: system_role,
            },
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.ASSISTANT_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: f"{welcome_message}. {bullet_points}{intro}",
            },
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: self.prompt,
            },
        ]

    def chat_request_body_factory(self, messages: list) -> dict[str, any]:
        return {SMARTER_CHAT_SESSION_KEY_NAME: self.session_key, "messages": messages}

    @classmethod
    def chat_request_factory(cls, request: HttpRequest, url: str, body: dict) -> HttpRequest:
        factory = RequestFactory()
        body_str = json.dumps(body) if body else ""

        parsed_url = urlparse(url)
        path = parsed_url.path
        new_request = factory.post(path, data=body_str, content_type="application/json")

        new_request.META = request.META.copy()
        new_request.META["HTTP_HOST"] = parsed_url.hostname
        new_request.META["SERVER_PORT"] = parsed_url.port
        new_request.META["QUERY_STRING"] = ""

        new_request.user = request.user

        if hasattr(request, "session"):
            new_request.session = request.session
        # pylint: disable=W0212
        if hasattr(request, "_messages"):
            new_request._messages = request._messages

        return new_request

    def handler(self, request, name, *args, **kwargs):
        # get the chat configuration for the ChatBot (name)
        chat_config: HttpResponse = ChatConfigView.as_view()(request, name=name)
        if chat_config.status_code != 200:
            raise APIV1CLIChatViewError(
                f"Internal error. Failed to get chat config for chatbot: {name} {chat_config.content}"
            )

        try:
            # bootstrap our chat session configuration
            chat_config: dict = json.loads(chat_config.content)
            self._chat_config = chat_config.get(SCLIResponseGet.DATA.value)
            self._session_key = self.chat_config.get(SMARTER_CHAT_SESSION_KEY_NAME)
            cache.set(key=self.cache_key, value=self.session_key, timeout=CACHE_EXPIRATION)
        except json.JSONDecodeError as e:
            raise APIV1CLIViewError(
                f"Misconfigured. Failed to cache session key for chat config: {chat_config.content}"
            ) from e

        # create a Smarter chatbot request body
        request_body = self.chat_request_body_factory(messages=self.messages)

        # create a Smarter chatbot request and prompt the chatbot
        chat_request = self.chat_request_factory(request=request, url=self.url_chatbot, body=request_body)
        chat_response = DefaultChatBotApiView.as_view()(request=chat_request, name=name)
        chat_response = json.loads(chat_response.content)

        response_data = chat_response.get(SmarterJournalApiResponseKeys.DATA)
        try:
            if not response_data:
                raise APIV1CLIChatViewError(f"Internal error. Chat response data key is missing: {chat_response}")

            response_body = response_data.get("body")
            if not response_body:
                # an internal error might have occurred, so look for an error key
                response_error = response_data.get("error")
                if response_error:
                    raise APIV1CLIChatViewError(f"Chat response error: {response_error}")
                raise APIV1CLIChatViewError(
                    f"Internal error. Chat response body and error keys are missing: {response_body}"
                )
        except APIV1CLIChatViewError as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                thing=SmarterJournalThings(SmarterJournalThings.CHAT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
            )

        # unescape the chat response body so that it looks
        # normal from the cli command line.
        body_dict = json.loads(response_body)
        chat_response[SmarterJournalApiResponseKeys.DATA]["body"] = body_dict

        data = {SmarterJournalApiResponseKeys.DATA: {"request": request_body, "response": chat_response}}
        return SmarterJournaledJsonResponse(
            request=request,
            data=data,
            thing=SmarterJournalThings(SmarterJournalThings.CHAT),
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
        )

    # pylint: disable=too-many-locals
    def post(self, request, name, *args, **kwargs):
        """
        Smarter API command-line interface 'chat' view. This is a non-brokered view
        that sends facilitates chat sessions to a ChatBot by creating a http post request
        to the ChatBot's published url. The chatbot is expected to be a Smarter chatbot
        that is capable of receiving a list of messages and returning a response in the
        smarter.sh/v1 protocol.

        Chats are based on sticky sessions that are identified by a cached session_key. The session_key is
        generated ....

        Args:
        - request: an authenticated Django HttpRequest object
        - name: str. the name of a ChatBot associated with the Account to which the authenticated user belongs.

        request body:
        - session_key: str. optional. the session_key for the chat session. if not provided then a new session_key will be generated.
        - prompt: str. the raw text of the prompt to send to the chatbot. This will be appended to the message list, if this is not a new session.

        url params:
        - new_session: str. optional flag. if present then the cache_key and session_key will be deleted.
        - uid: str. required. a unique identifier for the client. this is assumed to be a combination of the machine mac address and the hostname.

        """

        # validate the chatbot name, as this is the most likely point of failure
        try:
            ChatBot.objects.get(name=name, account=self.account)
        except ChatBot.DoesNotExist:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=APIV1CLIChatViewError(f"Chatbot {name} not found."),
                thing=SmarterJournalThings(SmarterJournalThings.CHAT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
            )

        # pylint: disable=W0718
        try:
            return self.handler(request, name, *args, **kwargs)
        except Exception as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=APIV1CLIChatViewError(f"Internal error. {e}"),
                thing=SmarterJournalThings(SmarterJournalThings.CHAT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
            )
