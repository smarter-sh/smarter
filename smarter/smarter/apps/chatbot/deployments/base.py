# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import logging
from typing import List

from cachetools import TTLCache, cached
from django.http import Http404, HttpResponseForbidden
from knox.auth import TokenAuthentication

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotApiUrlHelper,
    ChatBotPlugin,
)
from smarter.apps.chatbot.signals import chatbot_called
from smarter.apps.plugin.plugin import Plugin
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.drf.view_helpers import SmarterUnauthenticatedAPIView


logger = logging.getLogger(__name__)
cache = TTLCache(ttl=600, maxsize=1000)


class ChatBotApiBaseViewSet(SmarterUnauthenticatedAPIView):
    """
    Base viewset for all ChatBot APIs. Handles
    - api key authentication
    - Account and ChatBot initializations
    - dispatching.
    """

    account: Account = None
    chatbot: ChatBot = None
    plugins: List[Plugin] = None

    @cached(cache)
    def get_cached_helper(self, url, user):
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
            return True

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

        return False

    def dispatch(self, request, *args, **kwargs):
        helper = self.get_cached_helper(request.get_host(), request.user)
        if not helper.is_valid:
            return Http404()
        self.chatbot = helper.chatbot
        if helper.is_authentication_required and not self.smarter_api_authenticate(request):
            return HttpResponseForbidden()
        self.account = helper.account
        self.plugins = ChatBotPlugin().plugins(chatbot=self.chatbot)

        chatbot_called.send(sender=self.__class__, chatbot=self.chatbot, request=request, args=args, kwargs=kwargs)
        return super().dispatch(request, *args, **kwargs)
