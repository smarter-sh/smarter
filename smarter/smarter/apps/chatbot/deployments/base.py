# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import logging
from http import HTTPStatus
from typing import List

from cachetools import TTLCache, cached
from django.http import HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from knox.auth import TokenAuthentication
from rest_framework.views import APIView

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
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


logger = logging.getLogger(__name__)
cache = TTLCache(ttl=600, maxsize=1000)


class ChatBotApiBaseViewSet(SmarterAuthenticatedNeverCachedWebView):
    """
    Base viewset for all ChatBot APIs. Handles
    - api key authentication
    - Account and ChatBot initializations
    - dispatching.
    """

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
        logger.debug("ChatBotApiBaseViewSet.dispatch: url=%s", url)
        logger.debug("ChatBotApiBaseViewSet.dispatch: user=%s", request.user)
        self.user = request.user
        if request.user.is_authenticated:
            self.helper = self.get_cached_helper(url=url, user=request.user)
        else:
            self.helper = self.get_cached_helper(url=url)

        if not self.helper.is_valid:
            return HttpResponseNotFound(
                content={
                    "message": "Not Found. Please provide a valid ChatBot URL.",
                    "account": self.helper.account,
                    "chatbot": self.helper.chatbot,
                    "user": self.helper.user,
                    "url": self.helper.url,
                }
            )
        self.chatbot = self.helper.chatbot
        if self.helper.is_authentication_required and not self.smarter_api_authenticate(request):
            return HttpResponseForbidden(content={"message": "Forbidden. Please provide a valid API key."})
        self.account = self.helper.account
        self.plugins = ChatBotPlugin().plugins(chatbot=self.chatbot)

        self.user = self.user or account_admin_user(self.account)

        logger.debug("ChatBotApiBaseViewSet.dispatch: done. account=%s", self.account)
        logger.debug("ChatBotApiBaseViewSet.dispatch: done. chatbot=%s", self.chatbot)
        logger.debug("ChatBotApiBaseViewSet.dispatch: done. user=%s", self.user)
        logger.debug("ChatBotApiBaseViewSet.dispatch: done. plugins=%s", self.plugins)

        chatbot_called.send(sender=self.__class__, chatbot=self.chatbot, request=request, args=args, kwargs=kwargs)
        return super().dispatch(request, *args, **kwargs)

    # pylint: disable=W0613
    def get(self, request, *args, **kwargs):
        kwargs.get("chatbot_id", None)
        retval = {
            "message": "GET is not supported. Please use POST.",
            "chatbot": self.chatbot.name if self.chatbot else None,
            "mode": self.chatbot.mode(url=self.helper.url) if self.chatbot else None,
            "created": self.chatbot.created_at if self.chatbot else None,
            "updated": self.chatbot.updated_at if self.chatbot else None,
            "plugins": ChatBotPlugin.plugins_json(chatbot=self.chatbot) if self.chatbot else None,
            "account": self.account,
            "user": self.user,
        }
        return JsonResponse(data=retval, status=HTTPStatus.METHOD_NOT_ALLOWED)
