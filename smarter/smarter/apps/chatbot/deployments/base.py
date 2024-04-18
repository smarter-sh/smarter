# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import logging
from http import HTTPStatus
from typing import List

from cachetools import TTLCache, cached
from django.http import JsonResponse
from knox.auth import TokenAuthentication
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotApiUrlHelper,
    ChatBotPlugin,
)
from smarter.apps.chatbot.signals import chatbot_called
from smarter.apps.plugin.plugin import Plugin
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.drf.view_helpers import SmarterUnauthenticatedAPIView


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

cache = TTLCache(ttl=600, maxsize=1000)


class ChatBotApiBaseViewSet(SmarterUnauthenticatedAPIView):
    """
    Base viewset for all ChatBot APIs. Handles
    - api key authentication
    - Account and ChatBot initializations
    - dispatching.
    """

    http_method_names = ["get", "post", "options"]
    helper: ChatBotApiUrlHelper = None
    account: Account = None
    user: UserType = None
    chatbot: ChatBot = None
    plugins: List[Plugin] = None

    @property
    def is_web_platform(self):
        host = self.request.get_host()
        if host in smarter_settings.environment_domain:
            return True
        return False

    @cached(cache)
    def get_cached_helper(self, url, user: UserType = None) -> ChatBotApiUrlHelper:
        """
        Get the ChatBotApiUrlHelper object for the given url and user. This method is cached
        for 10 minutes because its a relatively expensive operation with multiple database queries.
        """
        return ChatBotApiUrlHelper(url=url, user=user)

    def smarter_api_authenticate(self, request) -> bool:
        """
        Authenticate the request against any api keys associated with the ChatBot.
        ChatBot is public if no API keys are associated with it. There are
        four levels of authentication:
        - if no API keys are associated with the ChatBot, then it is public.
        - otherwise, the authentication token (understood to be , "API key" from a customer perspective)
          must be valid as per knox authentication.
        - and, the User associated with the authentication token must also be associated with the Account
          to which the ChatBot belongs.
        - and, API key must be associated with the ChatBot
        """

        # if there are no API keys associated with the ChatBot, then it is public
        if not ChatBotAPIKey.objects.filter(chatbot=self.chatbot, api_key__is_active=True).exists():
            self.user = request.user
            return True

        # returns a tuple of (user, api_key) if the request is authenticated
        user, api_key = TokenAuthentication().authenticate(request)

        # the user associated with the API key must have a UserProfile
        # associated with the Account for the ChatBot.
        if not UserProfile.objects.filter(user=user, account=self.account).exists():
            url = request.build_absolute_uri()
            msg = f"Received url {url} from User {user} who is not associated with Account {self.account}"
            raise SmarterBusinessRuleViolation(message=msg)

        # the api_key must be associated with the ChatBot
        if not ChatBotAPIKey.objects.filter(api_key=api_key, chatbot=self.chatbot).exists():
            user_profile = UserProfile.objects.get(user=user)
            msg = f"Received api key {api_key.description} for User {user} of Account {user_profile.account.account_number} which is not associated with Chatbot {self.chatbot.name}"
            raise SmarterBusinessRuleViolation(message=msg)

        self.user = user
        return api_key is not None

    def dispatch(self, request, *args, **kwargs):
        url = request.build_absolute_uri()
        url = SmarterValidator.urlify(url)

        logger.info("ChatBotApiBaseViewSet.dispatch(): url=%s", url)
        logger.info("ChatBotApiBaseViewSet.dispatch(): user=%s", request.user)
        logger.info("ChatBotApiBaseViewSet.dispatch(): method=%s", request.method)  # Log the method

        self.helper = self.get_cached_helper(url=url)
        if not self.helper.is_valid:
            data = {
                "message": "Not Found. Please provide a valid ChatBot URL.",
                "account": self.helper.account.account_number if self.helper.account else None,
                "chatbot": self.helper.chatbot,
                "user": self.helper.user.username if self.helper.user else None,
                "url": self.helper.url,
            }
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST)
        if self.helper.is_authentication_required and not self.smarter_api_authenticate(request):
            data = {"message": "Forbidden. Please provide a valid API key."}
            return JsonResponse(data=data, status=HTTPStatus.FORBIDDEN)

        self.account = self.helper.account
        self.user = account_admin_user(self.account)
        self.chatbot = self.helper.chatbot
        self.plugins = ChatBotPlugin().plugins(chatbot=self.chatbot)

        logger.debug("ChatBotApiBaseViewSet.dispatch(): account=%s", self.account)
        logger.debug("ChatBotApiBaseViewSet.dispatch(): chatbot=%s", self.chatbot)
        logger.debug("ChatBotApiBaseViewSet.dispatch(): user=%s", self.user)
        logger.debug("ChatBotApiBaseViewSet.dispatch(): plugins=%s", self.plugins)

        chatbot_called.send(sender=self.__class__, chatbot=self.chatbot, request=request, args=args, kwargs=kwargs)
        return super().dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        response = Response()
        response["Access-Control-Allow-Origin"] = smarter_settings.environment_url
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "origin, content-type, accept"
        return response

    # pylint: disable=W0613
    def get(self, request, *args, **kwargs):
        kwargs.get("chatbot_id", None)
        retval = {
            "message": "GET is not supported. Please use POST.",
            "chatbot": self.chatbot.name if self.chatbot else None,
            "mode": self.chatbot.mode(url=self.helper.url) if self.chatbot else None,
            "created": self.chatbot.created_at.isoformat() if self.chatbot else None,
            "updated": self.chatbot.updated_at.isoformat() if self.chatbot else None,
            "plugins": ChatBotPlugin.plugins_json(chatbot=self.chatbot) if self.chatbot else None,
            "account": self.account.account_number if self.account else None,
            "user": self.user.username if self.user else None,
        }
        return JsonResponse(data=retval, status=HTTPStatus.OK)
