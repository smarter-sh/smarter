# pylint: disable=W0611
"""ChatBot api/v1/chatbots base view, for invoking a ChatBot."""
import json
import logging
from http import HTTPStatus
from typing import List

import waffle
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.chat.models import ChatHelper
from smarter.apps.chatbot.models import ChatBotHelper, ChatBotPlugin
from smarter.apps.chatbot.serializers import ChatBotSerializer
from smarter.apps.chatbot.signals import chatbot_called
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterWaffleSwitches
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.user import User, UserType
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.view_helpers import SmarterNeverCachedWebView


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    _session_key: str = None
    _name: str = None

    data: dict = {}
    chat_helper: ChatHelper = None
    request: HttpRequest = None
    http_method_names: list[str] = ["get", "post", "options"]
    plugins: List[PluginStatic] = None

    @property
    def session_key(self):
        return self._session_key

    @property
    def chatbot_id(self):
        return self._chatbot_id

    @property
    def chatbot_helper(self) -> ChatBotHelper:
        if self._chatbot_helper:
            return self._chatbot_helper
        # ensure that we have some combination of properties that can identify a chatbot
        if not (self.url or self.chatbot_id or (self.account and self.name)):
            return None
        self._chatbot_helper = ChatBotHelper(
            url=self.url, name=self.name, user=self.user, account=self.account, chatbot_id=self.chatbot_id
        )
        self._chatbot_id = self._chatbot_helper.chatbot_id
        self._url = self._chatbot_helper.url
        self._user = self._chatbot_helper.user
        self._account = self._chatbot_helper.account
        logger.info(
            "ChatBotHelper: %s initialized with url: %s id: %s", self._chatbot_helper, self.url, self.chatbot_id
        )
        return self._chatbot_helper

    @property
    def name(self):
        if not self._name:
            self._name = self.chatbot_helper.name if self._chatbot_helper else None
        return self._name

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

    def dispatch(self, request, *args, name: str = None, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)

        self.request = self.request or request
        self._user = self._user or request.user
        self._chatbot_id = kwargs.pop("chatbot_id")
        if self.chatbot:
            self._account = self.chatbot.account
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
            return retval

        self.plugins = ChatBotPlugin().plugins(chatbot=self.chatbot)

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s.dispatch(): account=%s", self.formatted_class_name, self.account)
            logger.info("%s.dispatch(): chatbot=%s", self.formatted_class_name, self.chatbot)
            logger.info("%s.dispatch(): user=%s", self.formatted_class_name, self.user)
            logger.info("%s.dispatch(): plugins=%s", self.formatted_class_name, self.plugins)

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s - name=%s", self.formatted_class_name, self.name)

        try:
            self.data = json.loads(request.body)
        except json.JSONDecodeError:
            self.data = {}
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s - data=%s", self.formatted_class_name, self.data)

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
