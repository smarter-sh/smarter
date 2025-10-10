# pylint: disable=W0611
"""ChatBot api/v1/chatbots base view, for invoking a ChatBot."""
import logging
import traceback
from http import HTTPStatus
from typing import List, Optional
from urllib.parse import urlparse

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.chatbot.exceptions import SmarterChatBotException
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
from smarter.apps.chatbot.serializers import ChatBotSerializer
from smarter.apps.chatbot.signals import chatbot_called
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import ChatHelper
from smarter.apps.prompt.providers.providers import chat_providers
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.view_helpers import SmarterNeverCachedWebView
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


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class ChatBotApiBaseViewSet(SmarterNeverCachedWebView):
    """
    Base viewset for all ChatBot APIs. Handles
    - api key authentication
    - Account and ChatBot initializations
    - dispatching.

    examples:
    - https://customer-support.3141-5926-5359.api.smarter.sh/
    - https://platform.smarter/workbench/example/
    - https://platform.smarter/api/v1/workbench/1/chat/

    """

    _chatbot_id: Optional[int] = None
    _chatbot_helper: Optional[ChatBotHelper] = None
    _chat_helper: Optional[ChatHelper] = None
    _name: Optional[str] = None

    http_method_names: list[str] = ["get", "post", "options"]
    plugins: Optional[List[PluginBase]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

    @property
    def chatbot_id(self):
        return self._chatbot_id

    @property
    def chat_helper(self) -> ChatHelper:
        if self._chat_helper:
            return self._chat_helper

        if self.session_key or self.chatbot:
            self._chat_helper = ChatHelper(
                request=self.smarter_request, session_key=self.session_key, chatbot=self.chatbot
            )
            if self._chat_helper:
                self.helper_logger(
                    f"{self.formatted_class_name} initialized with chat: {self.chat_helper.chat}, chatbot: {self.chatbot}"
                )
        else:
            raise SmarterChatBotException(
                f"ChatHelper not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )

        return self._chat_helper

    @property
    def chatbot_helper(self) -> Optional[ChatBotHelper]:
        if self._chatbot_helper:
            return self._chatbot_helper
        # ensure that we have some combination of properties that can identify a chatbot
        if not (self.url or self.chatbot_id or (self.account and self.name)):
            return None
        try:
            self._chatbot_helper = ChatBotHelper(
                request=self.smarter_request,
                name=self.name,
                chatbot_id=self.chatbot_id,
                # SmarterRequestMixin should have set these properties
                session_key=self.session_key,
                # and these, for AccountMixin,
                account=self.account,
                user=self.user,
                user_profile=self.user_profile,
            )
        # smarter.apps.chatbot.models.ChatBot.DoesNotExist: ChatBot matching query does not exist.
        except ChatBot.DoesNotExist as e:
            raise SmarterChatBotException(
                f"ChatBot not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            ) from e

        self._chatbot_id = self._chatbot_helper.chatbot_id
        if self._chatbot_id:
            logger.info(
                "%s: %s initialized ChatBotHelper with id: %s, url: %s",
                self.formatted_class_name,
                self._chatbot_helper,
                self._chatbot_id,
                self._url,
            )
        if self._chatbot_helper:
            logger.info(
                "%s: %s ChatBotHelper reinitializing user: %s, account: %s",
            )
            self._url = urlparse(self._chatbot_helper.url)  # type: ignore
            self._user = self._chatbot_helper.user
            self._account = self._chatbot_helper.account
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
        self._name = self._chatbot_helper.name if self._chatbot_helper else None

    @property
    def chatbot(self):
        return self.chatbot_helper.chatbot if self.chatbot_helper else None

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class} ChatBotApiBaseViewSet()"

    @property
    def url(self):
        try:
            return self._url
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s: Error getting url: %s", self.formatted_class_name, e)

    @property
    def is_web_platform(self):
        host = self.smarter_request.get_host()
        if host in smarter_settings.environment_platform_domain:
            return True
        return False

    def helper_logger(self, message: str):
        """
        Create a log entry
        """
        logger.info("%s: %s", self.formatted_class_name, message)

    def setup(self, request: WSGIRequest, *args, **kwargs):
        """
        Setup method for the ChatBot API base viewset.
        This method initializes the SmarterRequestMixin with the request,
        and sets up the ChatBotHelper and ChatHelper instances.
        """
        logger.info(
            "%s.setup() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
            args,
            kwargs,
        )
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request: WSGIRequest, *args, name: Optional[str] = None, **kwargs):
        """
        Setup method for the ChatBot API base viewset.
        This method initializes the ChatBotHelper and ChatHelper instances,
        sets up the request, and logs relevant information.
        """
        self._chatbot_id = kwargs.get("chatbot_id")
        if self._chatbot_id:
            kwargs.pop("chatbot_id")
        if self.chatbot:
            self.account = self.chatbot.account
        else:
            self._name = self._name or name
        if not self.chatbot:
            logger.error(
                "Could not initialize ChatBotHelper url: %s, name: %s, user: %s, account: %s, id: %s",
                self.url,
                self.name,
                self.user,
                self.account,
                self.chatbot_id,
            )
            return JsonResponse({}, status=HTTPStatus.NOT_FOUND.value)

        logger.info("%s.dispatch() - url=%s", self.formatted_class_name, self.url)
        logger.info("%s.dispatch() - id=%s", self.formatted_class_name, self.chatbot_id)
        logger.info("%s.dispatch() - name=%s", self.formatted_class_name, self.name)
        logger.info("%s.dispatch() - account=%s", self.formatted_class_name, self.account)
        logger.info("%s.dispatch() - chatbot=%s", self.formatted_class_name, self.chatbot)
        logger.info("%s.dispatch() - user=%s", self.formatted_class_name, request.user)
        logger.info("%s.dispatch() - method=%s", self.formatted_class_name, request.method)
        logger.info("%s.dispatch() - body=%s", self.formatted_class_name, request.body)
        logger.info("%s.dispatch() - headers=%s", self.formatted_class_name, request.META)

        if not self.chatbot_helper:
            raise SmarterChatBotException(
                f"ChatBotHelper not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
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
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST.value)
        if self.chatbot_helper.is_authentication_required and not request.user.is_authenticated:
            data = {"message": "Forbidden. Please provide a valid API key."}
            return JsonResponse(data=data, status=HTTPStatus.FORBIDDEN.value)

        self.plugins = ChatBotPlugin().plugins(chatbot=self.chatbot)

        if self.chatbot_helper.is_chatbot:
            logger.info("%s.dispatch(): account=%s", self.formatted_class_name, self.account)
            logger.info("%s.dispatch(): chatbot=%s", self.formatted_class_name, self.chatbot)
            logger.info("%s.dispatch(): user=%s", self.formatted_class_name, self.user)
            logger.info("%s.dispatch(): plugins=%s", self.formatted_class_name, self.plugins)
            logger.info("%s.dispatch(): name=%s", self.formatted_class_name, self.name)
            logger.info("%s.dispatch(): data=%s", self.formatted_class_name, self.data)
            if self.session_key:
                logger.info("%s.dispatch(): session_key=%s", self.formatted_class_name, self.session_key)
                logger.info("%s.dispatch(): chat_helper=%s", self.formatted_class_name, self.chat_helper)

        if self.chatbot_helper.is_chatbot and self.chat_helper:
            chatbot_called.send(sender=self.__class__, chatbot=self.chatbot, request=request, args=args, kwargs=kwargs)

        return super().dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        logger.info(
            "%s.options(): url=%s",
            self.formatted_class_name,
            self.chatbot_helper.url if self.chatbot_helper else "(Missing ChatBotHelper.url)",
        )
        response = Response()
        response["Access-Control-Allow-Origin"] = smarter_settings.environment_url
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "origin, content-type, accept"
        return response

    # pylint: disable=W0613
    def get(self, request, *args, name: Optional[str] = None, **kwargs):
        url = self.chatbot_helper.url if self.chatbot_helper else self.smarter_build_absolute_uri(request)
        logger.info("%s.get(): url=%s", self.formatted_class_name, url)
        logger.info("%s.get(): headers=%s", self.formatted_class_name, request.META)
        retval = {
            "message": "GET is not supported. Please use POST.",
            "chatbot": self.chatbot.name if self.chatbot else None,
            "mode": self.chatbot.mode(url=self.chatbot_helper.url) if self.chatbot and self.chatbot_helper else None,
            "created": self.chatbot.created_at.isoformat() if self.chatbot else None,
            "updated": self.chatbot.updated_at.isoformat() if self.chatbot else None,
            "plugins": ChatBotPlugin.plugins_json(chatbot=self.chatbot) if self.chatbot else None,
            "account": self.account.account_number if self.account else None,
            "user": self.user.username if self.user else None,
            "meta": self.chatbot_helper.to_json() if self.chatbot_helper else None,
        }
        return JsonResponse(data=retval, status=HTTPStatus.OK.value)

    # pylint: disable=W0613
    def post(self, request, *args, name: Optional[str] = None, **kwargs):
        """
        POST request handler for the Smarter Chat API. We need to parse the request host
        to determine which ChatBot instance to use. There are two possible hostname formats:

        URL with default api domain
        -------------------
        example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbot/
        where
         - `customer-service' == chatbot.name`
         - `3141-5926-5359 == chatbot.account.account_number`
         - `api.smarter.sh == smarter_settings.environment_api_domain`

        URL with custom domain
        -------------------
        example: https://api.smarter.sh/chatbot/
        where
         - `api.smarter.sh == chatbot.custom_domain`
         - `ChatBotCustomDomain.is_verified == True` noting that
           an asynchronous task has verified the domain NS records.

        The ChatBot instance hostname is determined by the following logic:
        `chatbot.hostname == chatbot.custom_domain or chatbot.default_host`
        """

        logger.info(
            "%s.post() - provider=%s", self.formatted_class_name, self.chatbot.provider if self.chatbot else None
        )
        logger.info("%s.post() - data=%s", self.formatted_class_name, self.data)
        logger.info("%s.post() - account: %s - %s", self.formatted_class_name, self.account, self.account_number)
        logger.info("%s.post() - user: %s", self.formatted_class_name, self.user)
        logger.info(
            "%s.post() - chat: %s",
            self.formatted_class_name,
            self.chat_helper.chat.account.account_number if self.chat_helper and self.chat_helper.chat else None,
        )
        logger.info("%s.post() - chatbot: %s", self.formatted_class_name, self.chatbot)
        logger.info("%s.post() - plugins: %s", self.formatted_class_name, self.plugins)

        if not self.chatbot:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException(
                    f"ChatBot not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
                ),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND.value,
                stack_trace=traceback.format_exc(),
            )
        handler = chat_providers.get_handler(provider=self.chatbot.provider)
        if not self.chat_helper:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException(
                    f"ChatHelper not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
                ),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND.value,
                stack_trace=traceback.format_exc(),
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
            status=HTTPStatus.OK.value,
            safe=False,
        )
        self.helper_logger(f"{self.formatted_class_name} response={response}")
        return response
