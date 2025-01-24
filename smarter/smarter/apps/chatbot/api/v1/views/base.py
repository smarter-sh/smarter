# pylint: disable=W0611
"""ChatBot api/v1/chatbots base view, for invoking a ChatBot."""
import logging
from http import HTTPStatus
from typing import List

import waffle

# from cachetools import TTLCache, cached
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.utils import account_for_user
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
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

# cache = TTLCache(ttl=600, maxsize=1000)


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class ChatBotApiBaseViewSet(SmarterNeverCachedWebView, AccountMixin):
    """
    Base viewset for all ChatBot APIs. Handles
    - api key authentication
    - Account and ChatBot initializations
    - dispatching.
    """

    _url: str = None
    request: HttpRequest = None
    http_method_names: list[str] = ["get", "post", "options"]
    _chatbot_helper: ChatBotHelper = None
    _chatbot: ChatBot = None
    plugins: List[PluginStatic] = None
    _session_key: str = None
    _name: str = None

    @property
    def session_key(self):
        return self._session_key

    @property
    def chatbot_helper(self) -> ChatBotHelper:
        return self._chatbot_helper

    @property
    def name(self):
        return self._name

    @property
    def chatbot(self):
        if not self._chatbot:
            self._chatbot_helper = ChatBotHelper(name=self.name, account=self.account)
            self._chatbot = self._chatbot_helper.chatbot if self._chatbot_helper.chatbot else None
        return self._chatbot

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
        self.request = self.request or request
        self._user = self._user or request.user
        self._name = self._name or name
        self._url = self.request.build_absolute_uri()
        self._url = SmarterValidator.urlify(self._url, environment=smarter_settings.environment)
        self._chatbot_helper = ChatBotHelper(url=self.url, name=self.name, user=self.user, account=self.account)

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s.dispatch(): chatbot: %s", self.formatted_class_name, self.chatbot_helper.chatbot)
            logger.info("%s.dispatch() - url=%s", self.formatted_class_name, self.url)
            logger.info("%s.dispatch() - headers=%s", self.formatted_class_name, request.META)
            logger.info("%s.dispatch() - user=%s", self.formatted_class_name, request.user)
            logger.info("%s.dispatch() - method=%s", self.formatted_class_name, request.method)
            logger.info("%s.dispatch() - body=%s", self.formatted_class_name, request.body)

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

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s.dispatch(): account=%s", self.formatted_class_name, self.account)
            logger.info("%s.dispatch(): chatbot=%s", self.formatted_class_name, self.chatbot)
            logger.info("%s.dispatch(): user=%s", self.formatted_class_name, self.user)
            logger.info("%s.dispatch(): plugins=%s", self.formatted_class_name, self.plugins)

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
            logger.info("%s.get(): url=%s", self.formatted_class_name, self.chatbot_helper.url)
            logger.info("%s.get(): headers=%s", self.formatted_class_name, request.META)
        kwargs.get("chatbot_id", None)
        retval = {
            "message": "GET is not supported. Please use POST.",
            "chatbot": self.chatbot.name if self.chatbot else None,
            "mode": self.chatbot.mode(url=self.chatbot_helper.url) if self.chatbot else None,
            "created": self.chatbot.created_at.isoformat() if self.chatbot else None,
            "updated": self.chatbot.updated_at.isoformat() if self.chatbot else None,
            "plugins": ChatBotPlugin.plugins_json(chatbot=self.chatbot) if self.chatbot else None,
            "account": self.account.account_number if self.account else None,
            "user": self.user.username if self.user else None,
            "meta": self.chatbot_helper.to_json(),
        }
        return JsonResponse(data=retval, status=HTTPStatus.OK)
