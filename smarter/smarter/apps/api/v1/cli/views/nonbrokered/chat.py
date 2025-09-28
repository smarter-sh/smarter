# pylint: disable=W0613
"""Smarter API command-line interface 'chat' view"""

import logging
import traceback
from http import HTTPStatus
from typing import Any, Optional

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request

from smarter.apps.chatbot.api.v1.views.default import DefaultChatbotApiView
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.prompt.models import Chat, ChatHistory
from smarter.apps.prompt.providers.const import OpenAIMessageKeys
from smarter.apps.prompt.views import ChatConfigView
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMMetadataKeys, SCLIResponseGet

from ..base import APIV1CLIViewError, CliBaseApiView


# for establishing a lifetime for chat sessions. we create a session_key, then cache it
# and reuse it until it eventually expires.
CACHE_EXPIRATION = 24 * 60 * 60  # 24 hours


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class APIV1CLIChatViewError(APIV1CLIViewError):
    """APIV1CLIChatViewError exception class"""

    @property
    def get_formatted_err_message(self):
        return "Smarter api v1 cli chat error"


class ApiV1CliChatBaseApiView(CliBaseApiView):
    """Smarter API command-line interface 'chat' view"""

    _cache_key: Optional[str] = None
    _data: Optional[dict] = None
    _name: Optional[str] = None
    _prompt: Optional[str] = None

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliChatBaseApiView()"

    @property
    def prompt(self) -> Optional[str]:
        """
        The chat prompt from the request body. This is a single raw text input
        from the user. This will need to be added to a message list and sent
        to the chatbot.
        """
        if self.is_config:
            # config views are not expected to have a prompt
            return None
        if self._prompt is None:
            self._prompt = self.data.get("prompt", None) if isinstance(self.data, dict) else None
            if not self._prompt:
                raise APIV1CLIChatViewError(
                    f"Internal error. 'prompt' key is missing from the request body. self.data: {self.data}"
                )
            logger.info("%s.prompt() found prompt: %s", self.formatted_class_name, self._prompt)
        return self._prompt

    @property
    def new_session(self) -> bool:
        """
        True if the new_session url parameter was passed and is set to 'true'

        example: http://localhost:8000/api/v1/cli/chat/smarter/?new_session=false&uid=mcdaniel
        """
        if not self.params:
            return False
        if self.params.get("new_session", "false").lower() not in ["true", "false"]:
            bad_value = self.params.get("new_session")
            raise APIV1CLIChatViewError(
                f"Invalid value '{bad_value}' provided for url param new_session. Must be 'true' or 'false'."
            )
        return str(self.params.get("new_session", "false")).lower() == "true"

    @property
    def name(self) -> Optional[str]:
        """The name of the ChatBot. This is passed as a url slug."""
        return self._name

    def validate(self):
        """
        common validations for the chat views. This is called before dispatch() and is used to
        """

    def initial(self, request: Request, *args, **kwargs):
        """
        Initialize the view. This is called by DRF after setup() but before dispatch().

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
        super().initial(request, *args, **kwargs)
        self._name = kwargs.get(SAMMetadataKeys.NAME.value)
        logger.info("%s.initial() chat view name: %s", self.formatted_class_name, self.name)

        if not self.data and not self.is_config:
            raise APIV1CLIChatViewError(
                f"Internal error. Request body is empty. This is intended to be a json object with a 'prompt' key and an optional 'session_key' key. url: {self.url}"
            )

        if not self.uid:
            raise APIV1CLIChatViewError(
                f"Internal error. UID is missing. This is intended to be a unique identifier for the client, passed as a url param named 'uid'. url: {self.url}"
            )

        # if the new_session url parameter was passed and is set to True
        # then we will delete the cache_key and the session_key.
        if self.new_session:
            logger.info(
                "%s.initial() new_session is True, resetting the session_key and deleting cache_key: %s",
                self.formatted_class_name,
                self.cache_key,
            )
            self._session_key = self.generate_session_key()
            cache.delete(self.cache_key)
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info("%s.initial() deleted cache_key: %s", self.formatted_class_name, self.cache_key)

        # 1.) attempt to retrieve a session_key from the cache. if we get a hit
        # then we will update the request body with the session_key
        # and pass it along to the ChatConfigView.
        session_key = cache.get(self.cache_key)
        if session_key is not None:
            logger.info(
                "%s.initial() resetting session_key from %s to cached key: %s",
                self.formatted_class_name,
                self.session_key,
                session_key,
            )
            self._session_key = session_key

        # 3.) at this point we either have a session_key from the cache, or from the request body
        #     or from SmarterRequestMixin(). Otherwise, this will raise a SmarterValueError.
        if self.session_key:
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info(
                    "%s.initial() caching session_key for chat config: %s", self.formatted_class_name, self.session_key
                )
            if isinstance(self.data, dict):
                new_body = self.data.copy()
                new_body[SMARTER_CHAT_SESSION_KEY_NAME] = self.session_key
                new_body = json.dumps(new_body)
            else:
                new_body = json.dumps({SMARTER_CHAT_SESSION_KEY_NAME: self.session_key})

            # pylint: disable=W0212
            request._body = new_body.encode("utf-8")

        self.validate()


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
    - smarter/apps/workbench/data/chat_config.json
    - smarter/apps/workbench/data/request.json
    - smarter/apps/workbench/data/response.json
    """

    _chat: Optional[Chat] = None
    _chat_config: dict = {}
    _chat_history: Optional[ChatHistory] = None
    _messages: Optional[list[dict[str, str]]] = None

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliChatApiView()"

    @property
    def chat_config(self) -> dict:
        """The chat configuration dict."""
        return self._chat_config

    @property
    def chatbot_config(self) -> dict[str, Any]:
        """The chatbot configuration dict."""
        return self.chat_config.get("chatbot", {})

    @property
    def url_chatbot(self) -> Optional[str]:
        """The url of the chatbot."""
        return self.chatbot_config.get("url_chatbot", None)

    @property
    def chat(self) -> Optional[Chat]:
        """The chat object for the session_key."""
        if self._chat:
            return self._chat
        if self.session_key:
            self._chat = Chat.objects.get(session_key=self.session_key)

    @property
    def chat_history(self) -> Optional[ChatHistory]:

        if not self._chat_history:
            if self.chat:
                self._chat_history = ChatHistory.objects.filter(chat=self.chat).latest()
        return self._chat_history

    @property
    def messages(self) -> Optional[list[dict[str, str]]]:
        """The message list for the chat."""
        if self._messages:
            return self._messages

        # the cli is forcing a new session, so disregard the chat history
        # and create a new message list that includes the welcome message.
        if self.new_session:
            self._messages = self.new_message_list_factory()
        else:
            # try to get the messages from the chat history, is it exists
            messages: Optional[list] = (
                self.data.get("messages")
                if isinstance(self.data, dict) and isinstance(self.data.get("messages"), list)
                else None
            )
            if messages:
                messages.append({"role": "user", "content": self.prompt})
            else:
                # otherwise, create a new message list
                self._messages = self.new_message_list_factory()
        logger.info("%s.messages() value is set: %s", self.formatted_class_name, self._messages)
        return self._messages

    def new_message_list_factory(self) -> list[dict[str, str]]:

        logger.info("%s.new_message_list_factory() called", self.formatted_class_name)

        system_dict: Optional[dict] = None
        welcome_dict: Optional[dict] = None
        prompt_dict: Optional[dict] = None

        system_role: str = self.chatbot_config.get(
            "default_system_role",
            self.chat_config.get("default_system_role", smarter_settings.llm_default_system_role),
        )
        system_dict = {
            OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
            OpenAIMessageKeys.MESSAGE_CONTENT_KEY: system_role,
        }
        welcome_message: Optional[str] = self.chatbot_config.get("app_welcome_message")
        example_prompts: Optional[list[str]] = self.chatbot_config.get("app_example_prompts")
        if example_prompts and welcome_message:
            app_assistant: str = self.chatbot_config.get("app_assistant", "a chatbot")
            bullet_points = "\n".join(f"    - {prompt}" for prompt in example_prompts) if example_prompts else ""
            bullet_points = "Following are some example prompts:\n\n" + bullet_points + "\n\n"
            intro = f"I'm {app_assistant}, how can I assist you today?"
            welcome_dict = {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.ASSISTANT_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: f"{welcome_message}. {bullet_points}{intro}",
            }

        prompt_dict = {
            OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
            OpenAIMessageKeys.MESSAGE_CONTENT_KEY: self.prompt,
        }

        retval = [system_dict]
        if welcome_dict:
            retval.append(welcome_dict)
        retval.append(prompt_dict)

        logger.info("%s.new_message_list_factory() retval: %s", self.formatted_class_name, retval)
        return retval

    def chat_request_body_factory(self) -> dict[str, Any]:
        retval = {SMARTER_CHAT_SESSION_KEY_NAME: self.session_key, "messages": self.messages}
        logger.info("%s.chat_request_body_factory() retval: %s", self.formatted_class_name, retval)
        return retval

    def chat_request_factory(self, request_body: dict) -> HttpRequest:
        """Create a new request for the chatbot API."""
        if self.parsed_url is None:
            raise SmarterConfigurationError(
                f"Internal error. The parsed_url is None. This should never happen. url: {self.url}"
            )
        if not isinstance(request_body, dict):
            raise SmarterConfigurationError(
                f"Internal error. The request_body must be a dict, got {type(request_body)}. url: {self.url}"
            )
        factory = RequestFactory()
        new_request = factory.post(self.parsed_url.path, data=request_body, content_type="application/json")
        new_request.META = self.request.META.copy()
        new_request.META["HTTP_HOST"] = self.parsed_url.hostname
        new_request.META["SERVER_PORT"] = self.parsed_url.port
        new_request.META["QUERY_STRING"] = ""
        new_request.user = self.request.user if self.request and self.request.user else None  # type: ignore[union-attr]
        new_request.session = self.request.session if self.request and hasattr(self.request, "session") else None  # type: ignore[union-attr]

        return new_request

    def handler(self, request, name, *args, **kwargs):
        # get the chat configuration for the ChatBot (name)
        logger.info(
            "%s.handler() 1. name: %s url: %s data: %s session_key: %s, new session: %s",
            self.formatted_class_name,
            name,
            self.url,
            self.data,
            self.session_key,
            self.new_session,
        )

        chat_config: JsonResponse = ChatConfigView.as_view()(request, name=name, session_key=self.session_key)  # type: ignore[return-value]
        if not isinstance(chat_config, JsonResponse):
            raise APIV1CLIChatViewError(
                f"Internal error. Chat config view did not return a JsonResponse. chat_config: {chat_config}"
            )
        if chat_config.status_code != 200:  # type: ignore[union-attr]
            raise APIV1CLIChatViewError(
                f"Internal error. Failed to get chat config for chatbot: {name} {chat_config.get('content')}"
            )
        logger.info("%s.handler() 2. chat_config: %s %s", self.formatted_class_name, chat_config, type(chat_config))

        try:
            # bootstrap our chat session configuration
            chat_config_content = chat_config.content
            if chat_config_content is None:
                raise APIV1CLIViewError(
                    f"Internal error. Chat config 'content' is None. This should never happen. chat_config: {chat_config}"
                )
            chat_config_content = (
                chat_config_content.decode("utf-8") if isinstance(chat_config_content, bytes) else chat_config_content
            )
            chat_config: dict = json.loads(chat_config_content)
            self._chat_config = chat_config.get(SCLIResponseGet.DATA.value, {})
            session_key = self.chat_config.get(SMARTER_CHAT_SESSION_KEY_NAME)
            if session_key is not None:
                self._session_key = session_key
                logger.info(
                    "%s.handler() initialized session_key from chat_config: %s",
                    self.formatted_class_name,
                    self.session_key,
                )
            cache.set(key=self.cache_key, value=self.session_key, timeout=CACHE_EXPIRATION)
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info(
                    "%s.handler() caching session_key for chat config: %s",
                    self.formatted_class_name,
                    self.session_key,
                )
        except json.JSONDecodeError as e:
            raise APIV1CLIViewError(f"Misconfigured. Failed to cache session key for chat config: {chat_config}") from e
        except TypeError as e:
            raise APIV1CLIViewError(f"Internal error. Chat config 'content' is missing: {chat_config}") from e

        logger.info(
            "%s.handler() 3. config: %s",
            self.formatted_class_name,
            json.dumps(self.chat_config),
        )

        # create a Smarter chatbot request body
        request_body = self.chat_request_body_factory()

        # create a Smarter chatbot request and prompt the chatbot
        chat_request = self.chat_request_factory(request_body=request_body)
        chat_response = DefaultChatbotApiView.as_view()(request=chat_request, name=name)
        if not isinstance(chat_response, JsonResponse):
            raise APIV1CLIChatViewError(
                f"Internal error. Chat response is not a JsonResponse. chat_response: {chat_response}"
            )
        chat_response = json.loads(chat_response.content)

        response_data = chat_response.get(SmarterJournalApiResponseKeys.DATA)
        logger.info(
            "%s.handler() 4. response_data: %s",
            self.formatted_class_name,
            json.dumps(response_data),
        )
        try:
            if not response_data:
                raise APIV1CLIChatViewError(f"Internal error. Chat response key 'data' is missing: {chat_response}")

            response_body = response_data.get("body")
            if not response_body:
                # an internal error might have occurred, so look for an error key
                response_error = response_data.get("error")
                if response_error:
                    raise APIV1CLIChatViewError(f"Chat response error: {response_error}")
                raise APIV1CLIChatViewError(f"Internal error: {response_data}")
        except APIV1CLIChatViewError as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                thing=SmarterJournalThings(SmarterJournalThings.CHAT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                stack_trace=traceback.format_exc(),
            )

        # unescape the chat response body so that it looks
        # normal from the cli command line.
        body_dict = json.loads(response_body)
        chat_response[SmarterJournalApiResponseKeys.DATA]["body"] = body_dict

        data = {SmarterJournalApiResponseKeys.DATA: {"request": request_body, "response": chat_response}}
        logger.info("%s.handler() 5. data: %s", self.formatted_class_name, json.dumps(data))
        return SmarterJournaledJsonResponse(
            request=request,
            data=data,
            thing=SmarterJournalThings(SmarterJournalThings.CHAT),
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
        )

    def validate(self):
        """
        Validate the request body and url parameters. Note that we are not necessarily expecting a complete
        set of messages. The message list + the prompt will be sent to the chatbot, which is responsible
        for ensuring that the system prompt is included in the request.

        example request body:
        {
            "session_key": "45089cdcbcbc2ded87da784afd0e368ddece23ca9fb61260cf43c58a708e05e1",
            "messages": [
                {
                "role": "user",
                "content": "hello world"
                }
            ],
            "prompt": "who's your daddy?"
        }
        """
        super().validate()
        if not self.prompt and not self.is_config:
            raise APIV1CLIChatViewError("Internal error. 'prompt' key is missing from the request body.")
        messages = self.data.get("messages", None) if isinstance(self.data, dict) else None
        if messages:
            try:
                messages = messages if isinstance(messages, list) else json.loads(messages)
            except json.JSONDecodeError as e:
                raise APIV1CLIChatViewError(f"Internal error. Failed to decode messages: {messages}") from e
            if not isinstance(messages, list):
                raise APIV1CLIChatViewError(f"Internal error. Messages must be a list: {messages}")
        session_key = self.data.get(SMARTER_CHAT_SESSION_KEY_NAME, None) if isinstance(self.data, dict) else None

        if session_key:
            SmarterValidator.validate_session_key(session_key=session_key)

    # pylint: disable=too-many-locals
    @csrf_exempt
    def post(self, request, name, *args, **kwargs):
        """
        Smarter API command-line interface 'chat' view. This is a non-brokered view
        that sends chat sessions to a ChatBot by creating a http post request
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
        except ChatBot.DoesNotExist as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                thing=SmarterJournalThings(SmarterJournalThings.CHAT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND,
                stack_trace=traceback.format_exc(),
                description=f"{self.formatted_class_name}.post() ChatBot {name} not found for account {self.account}",
            )

        # pylint: disable=W0718
        try:
            response = self.handler(request, name, *args, **kwargs)
            return response
        except Exception as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=e,
                thing=SmarterJournalThings(SmarterJournalThings.CHAT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                stack_trace=traceback.format_exc(),
            )
