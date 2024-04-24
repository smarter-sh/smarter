"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import hashlib
import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.chatbot.api.v0.serializers import (
    ChatBotPluginSerializer,
    ChatBotSerializer,
)
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
from smarter.lib.django.user import UserType
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


MAX_RETURNED_PLUGINS = 10


logger = logging.getLogger(__name__)


# pylint: disable=R0902
@method_decorator(login_required, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
class ChatConfigView(View):
    """
    Chat config view for smarter web. This view is protected and requires the user
    to be authenticated. It works with any ChatBots but is aimed at chatbots running
    inside the web console in sandbox mode.

    example: https://sales.3141-5926-5359.alpha.api.smarter.sh/chatbot/config/
    """

    _sandbox_mode: bool = True
    request: None
    helper: ChatBotHelper = None
    account: Account = None
    user: UserType = None
    user_profile: UserProfile = None
    chatbot: ChatBot = None
    url: str = None
    session_key: str = None

    @property
    def ip_address(self):
        return self.request.META.get("REMOTE_ADDR", "")

    @property
    def user_agent(self):
        return self.request.META.get("HTTP_USER_AGENT", "")

    @property
    def unique_client_string(self):
        return f"{self.account.account_number}{self.chatbot.id}{self.user_agent}{self.ip_address}"

    @property
    def client_key(self):
        return hashlib.sha256(self.unique_client_string.encode()).hexdigest()

    def create_session_key(self):
        key_string = self.unique_client_string + str(datetime.now())
        return hashlib.sha256(key_string.encode()).hexdigest()

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        name = kwargs.pop("name", None)
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            body = {}
        logger.info("ChatConfigView: %s", body)

        self.user = request.user
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.account = self.user_profile.account

        self._sandbox_mode = name is not None
        self.url = request.build_absolute_uri()
        self.helper = ChatBotHelper(url=self.url, user=self.user_profile.user, account=self.account, name=name)
        self.chatbot = self.helper.chatbot
        if not self.chatbot:
            return HttpResponseNotFound()

        self.session_key = body.get("session_key") or self.create_session_key()
        return super().dispatch(request, *args, **kwargs)

    # pylint: disable=unused-argument
    def post(self, request, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        return JsonResponse(data=self.config())

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        return JsonResponse(data=self.config())

    @property
    def sandbox_mode(self):
        return self._sandbox_mode

    def config(self) -> dict:
        """
        React context for all templates that render
        a React app.
        """
        chatbot_serializer = ChatBotSerializer(self.chatbot) if self.chatbot else None

        # plugins context. the main thing we need here is to constrain the number of plugins
        # returned to some reasonable number, since we'll probaably have cases where
        # the chatbot has a lot of plugins (hundreds, thousands...).
        chatbot_plugins_count = ChatBotPlugin.objects.filter(chatbot=self.chatbot).count()
        chatbot_plugins = ChatBotPlugin.objects.filter(chatbot=self.chatbot).order_by("-pk")[:MAX_RETURNED_PLUGINS]
        chatbot_plugin_serializer = ChatBotPluginSerializer(chatbot_plugins, many=True)

        retval = {
            "session_key": self.session_key,
            "sandbox_mode": self.sandbox_mode,
            "chatbot": chatbot_serializer.data,
            "meta_data": self.helper.to_json(),
            "plugins": {
                "meta_data": {
                    "total_plugins": chatbot_plugins_count,
                    "plugins_returned": len(chatbot_plugins),
                },
                "plugins": chatbot_plugin_serializer.data,
            },
        }
        return retval


@method_decorator(csrf_exempt, name="dispatch")
class ChatAppView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chat app view for smarter web. This view is protected and requires the user
    to be authenticated. It works with deployed ChatBots. The url is expected to
    be in one of three formats.

    Sandbox mode:
    - http://smarter.querium.com/chatapp/hr/
    - http://127.0.0.1:8000/chatapp/<str:name>/

    Production mode:
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatapp/
    - https://hr.smarter.querium.com/chatapp/


    It serves the chat app's main page within the Smarter
    dashboard web app. React builds are served from the static directory and the
    build assets use hashed file names, so we probably don't really need to worry
    about cache behavior. However, we're using the `never_cache` decorator to
    ensure that the browser doesn't cache the page itself, which could cause
    problems if the user logs out and then logs back in without refreshing the
    page.

    template_path: Keep in mind that the index.html entry point for the React
    app is served from the static directory, not the templates directory. This
    is because the React app is built and served as a static asset. The
    `template_path` attribute is used to specify the path to the final index.html file
    which is first built by npm and then later copied to the Django static directory
    via the Django manage.py `collectstatic` command. This is why the path is
    relative to the static directory, not the templates directory.
    """

    _sandbox_mode: bool = False

    template_path = "index.html"
    chatbot: ChatBot = None
    helper: ChatBotHelper = None
    url: str = None

    @property
    def sandbox_mode(self):
        return self._sandbox_mode

    def dispatch(self, request, *args, **kwargs):
        name = kwargs.pop("name", None)
        self._sandbox_mode = name is not None
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 300:
            return response
        self.url = request.build_absolute_uri()
        self.helper = ChatBotHelper(url=self.url, user=self.user_profile.user, account=self.account, name=name)
        self.chatbot = self.helper.chatbot
        if not self.chatbot:
            return HttpResponseNotFound()
        return render(request, self.template_path)
