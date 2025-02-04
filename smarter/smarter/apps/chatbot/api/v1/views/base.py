# pylint: disable=W0611
"""ChatBot api/v1/chatbots base view, for invoking a ChatBot."""
import json
import logging
from http import HTTPStatus
from typing import List

import waffle
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.chat.models import ChatHelper
from smarter.apps.chat.providers.providers import chat_providers
from smarter.apps.chatbot.exceptions import SmarterChatBotException
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
from smarter.apps.chatbot.serializers import ChatBotSerializer
from smarter.apps.chatbot.signals import chatbot_called
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME, SmarterWaffleSwitches
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.user import User, UserType
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.view_helpers import SmarterNeverCachedWebView
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)


logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class ChatBotApiBaseViewSet(SmarterNeverCachedWebView, AccountMixin):
    """
    Base viewset for all ChatBot APIs. Handles
    - api key authentication
    - Account and ChatBot initializations
    - dispatching.
    """

    _chatbot_id: int = None
    _url: str = None
    _chatbot_helper: ChatBotHelper = None
    _chat_helper: ChatHelper = None
    _session_key: str = None
    _name: str = None

    data: dict = {}
    request: HttpRequest = None
    http_method_names: list[str] = ["get", "post", "options"]
    plugins: List[PluginStatic] = None

    @property
    def session_key(self):
        # Initialize the chat session for this request. session_key is generated
        # and managed by the /config/ endpoint for the chatbot
        #
        # examples:
        # - https://customer-support.3141-5926-5359.api.smarter.sh/
        # - https://platform.smarter/chatbots/example/
        # - https://platform.smarter/api/v1/chatbots/1/chat/
        #
        # The React app calls this endpoint at app initialization to get a
        # json dict that includes, among other pertinent info, this session_key
        # which uniquely identifies the device and the individual chatbot session
        # for the device.
        #
        # the session_key is intended to be sent in the body of the request
        # as a key-value pair, e.g. {"session_key": "1234567890"}
        #
        # But, this method will also check the request headers for the session_key.
        self._session_key = self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
        if not self._session_key:
            self._session_key = self.get_cookie_value(SMARTER_CHAT_SESSION_KEY_NAME)
        if self._session_key:
            SmarterValidator.validate_session_key(self._session_key)
        return self._session_key

    @property
    def chatbot_id(self):
        return self._chatbot_id

    @property
    def chat_helper(self) -> ChatHelper:
        if self._chat_helper:
            return self._chat_helper
        if self.session_key or self.chatbot:
            self._chat_helper = ChatHelper(request=self.request, session_key=self.session_key, chatbot=self.chatbot)
            if self._chat_helper:
                self.helper_logger(
                    (
                        "%s initialized with chat: %s, chatbot: %s",
                        self.formatted_class_name,
                        self.chat_helper.chat,
                        self.chatbot,
                    )
                )

        return self._chat_helper

    @property
    def chatbot_helper(self) -> ChatBotHelper:
        if self._chatbot_helper:
            return self._chatbot_helper
        # ensure that we have some combination of properties that can identify a chatbot
        if not (self.url or self.chatbot_id or (self.account and self.name)):
            return None
        try:
            self._chatbot_helper = ChatBotHelper(request=self.request, name=self.name, chatbot_id=self.chatbot_id)
        # smarter.apps.chatbot.models.ChatBot.DoesNotExist: ChatBot matching query does not exist.
        except ChatBot.DoesNotExist as e:
            raise SmarterChatBotException("ChatBot not found") from e

        self._chatbot_id = self._chatbot_helper.chatbot_id
        self._url = self._chatbot_helper.url
        self._user = self._chatbot_helper.user
        self._account = self._chatbot_helper.account
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_HELPER_LOGGING):
            logger.info(
                "%s: %s initialized with url: %s id: %s",
                self.formatted_class_name,
                self._chatbot_helper,
                self.url,
                self.chatbot_id,
            )
        return self._chatbot_helper

    @property
    def name(self):
        if self._name:
            return self._name
        self._name = self.chatbot_helper.name if self._chatbot_helper else None

    @property
    def chatbot(self):
        return self.chatbot_helper.chatbot if self.chatbot_helper else None

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

    @property
    def url(self):
        return self._url

    @property
    def is_web_platform(self):
        host = self.request.get_host()
        if host in smarter_settings.environment_domain:
            return True
        return False

    def get_cookie_value(self, cookie_name):
        """
        Retrieve the value of a cookie from the request object.

        :param request: Django HttpRequest object
        :param cookie_name: Name of the cookie to retrieve
        :return: Value of the cookie or None if the cookie does not exist
        """
        if self.request and self.request.COOKIES:
            return self.request.COOKIES.get(cookie_name)

    def helper_logger(self, message: str):
        """
        Create a log entry
        """
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info(f"{self.formatted_class_name}: {message}")

    def dispatch(self, request: WSGIRequest, *args, name: str = None, **kwargs):
        AccountMixin.__init__(self, user=request.user)
        self.request = request
        self._chatbot_id = kwargs.get("chatbot_id")
        if self._chatbot_id:
            kwargs.pop("chatbot_id")
        if self.chatbot:
            self.account = self.chatbot.account
        else:
            self._name = self._name or name
            self._url = self.request.build_absolute_uri()
            self._url = SmarterValidator.urlify(self._url, environment=smarter_settings.environment)
        if not self.chatbot:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
                logger.error(
                    "Could not initialize ChatBotHelper url: %s, name: %s, user: %s, account: %s, id: %s",
                    self.url,
                    self.name,
                    self.user,
                    self.account,
                    self.chatbot_id,
                )
            return JsonResponse({}, status=HTTPStatus.NOT_FOUND)

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s.dispatch() - url=%s", self.formatted_class_name, self.url)
            logger.info("%s.dispatch() - id=%s", self.formatted_class_name, self.chatbot_id)
            logger.info("%s.dispatch() - name=%s", self.formatted_class_name, self.name)
            logger.info("%s.dispatch() - account=%s", self.formatted_class_name, self.account)
            logger.info("%s.dispatch() - chatbot=%s", self.formatted_class_name, self.chatbot)
            logger.info("%s.dispatch() - user=%s", self.formatted_class_name, request.user)
            logger.info("%s.dispatch() - method=%s", self.formatted_class_name, request.method)
            logger.info("%s.dispatch() - body=%s", self.formatted_class_name, request.body)
            logger.info("%s.dispatch() - headers=%s", self.formatted_class_name, request.META)

        if not self.chatbot_helper.is_valid:
            data = {
                "data": {
                    "error": {
                        "message": "Could not initialize ChatBot object.",
                        "account": self.account.account_number if self.account else None,
                        "chatbot": ChatBotSerializer(self.chatbot).data if self.chatbot else None,
                        "user": self.user.username if self.user else None,
                        "name": self.chatbot_helper.name,
                        "url": self.chatbot_helper.url,
                    },
                },
            }
            self.chatbot_helper.log_dump()
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST)
        if self.chatbot_helper.is_authentication_required and not request.user.is_authenticated:
            data = {"message": "Forbidden. Please provide a valid API key."}
            return JsonResponse(data=data, status=HTTPStatus.FORBIDDEN)

        self.plugins = ChatBotPlugin().plugins(chatbot=self.chatbot)

        try:
            logger.info("%s.dispatch(): request.body=%s", self.formatted_class_name, request.body)
            self.data = json.loads(request.body)
        except json.JSONDecodeError:
            self.data = {}

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s.dispatch(): account=%s", self.formatted_class_name, self.account)
            logger.info("%s.dispatch(): chatbot=%s", self.formatted_class_name, self.chatbot)
            logger.info("%s.dispatch(): user=%s", self.formatted_class_name, self.user)
            logger.info("%s.dispatch(): plugins=%s", self.formatted_class_name, self.plugins)
            logger.info("%s.dispatch(): name=%s", self.formatted_class_name, self.name)
            logger.info("%s.dispatch(): data=%s", self.formatted_class_name, self.data)
            logger.info("%s.dispatch(): session_key=%s", self.formatted_class_name, self.session_key)
            logger.info("%s.dispatch(): chat_helper=%s", self.formatted_class_name, self.chat_helper)

        chatbot_called.send(sender=self.__class__, chatbot=self.chatbot, request=request, args=args, kwargs=kwargs)

        return super().dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s.options(): url=%s", self.formatted_class_name, self.chatbot_helper.url)
        response = Response()
        response["Access-Control-Allow-Origin"] = smarter_settings.environment_url
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "origin, content-type, accept"
        return response

    # pylint: disable=W0613
    def get(self, request, *args, name: str = None, **kwargs):
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            url = self.chatbot_helper.url if self.chatbot_helper else request.build_absolute_uri()
            logger.info("%s.get(): url=%s", self.formatted_class_name, url)
            logger.info("%s.get(): headers=%s", self.formatted_class_name, request.META)
        retval = {
            "message": "GET is not supported. Please use POST.",
            "chatbot": self.chatbot.name if self.chatbot else None,
            "mode": self.chatbot.mode(url=self.chatbot_helper.url) if self.chatbot else None,
            "created": self.chatbot.created_at.isoformat() if self.chatbot else None,
            "updated": self.chatbot.updated_at.isoformat() if self.chatbot else None,
            "plugins": ChatBotPlugin.plugins_json(chatbot=self.chatbot) if self.chatbot else None,
            "account": self.account.account_number if self.account else None,
            "user": self.user.username if self.user else None,
            "meta": self.chatbot_helper.to_json() if self.chatbot_helper else None,
        }
        return JsonResponse(data=retval, status=HTTPStatus.OK)

    # pylint: disable=W0613
    def post(self, request, *args, name: str = None, **kwargs):
        """
        POST request handler for the Smarter Chat API. We need to parse the request host
        to determine which ChatBot instance to use. There are two possible hostname formats:

        URL with default api domain
        -------------------
        example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbot/
        where
         - `customer-service' == chatbot.name`
         - `3141-5926-5359 == chatbot.account.account_number`
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

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info(
                "%s.post() - provider=%s", self.formatted_class_name, self.chatbot.provider if self.chatbot else None
            )
            logger.info("%s.post() - data=%s", self.formatted_class_name, self.data)
            logger.info("%s.post() - account: %s", self.formatted_class_name, self.account)
            logger.info("%s.post() - user: %s", self.formatted_class_name, self.user)
            logger.info(
                "%s.post() - chat: %s", self.formatted_class_name, self.chat_helper.chat if self.chat_helper else None
            )
            logger.info("%s.post() - chatbot: %s", self.formatted_class_name, self.chatbot)
            logger.info("%s.post() - plugins: %s", self.formatted_class_name, self.plugins)

        if not self.chatbot:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException("ChatBot not found"),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND,
            )
        handler = chat_providers.get_handler(provider=self.chatbot.provider)
        if not self.chat_helper:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException("ChatHelper not found"),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND,
            )
        response = handler(chat=self.chat_helper.chat, data=self.data, plugins=self.plugins, user=self.user)
        response = {
            SmarterJournalApiResponseKeys.DATA: response,
        }
        response = SmarterJournaledJsonResponse(
            request=request,
            data=response,
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
            thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
            status=HTTPStatus.OK,
            safe=False,
        )
        self.helper_logger(("%s response=%s", self.formatted_class_name, response))
        return response
