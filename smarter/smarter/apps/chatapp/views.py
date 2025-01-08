"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import datetime
import hashlib
import json
import logging
import urllib.parse
from datetime import datetime
from http import HTTPStatus

import waffle
from django.db import models
from django.http import HttpResponseNotFound
from django.shortcuts import render

# from django.utils.decorators import method_decorator
from django.views import View

# from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.utils import smarter_admin_user_profile
from smarter.apps.chat.models import Chat, ChatHelper
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
from smarter.apps.chatbot.serializers import ChatBotPluginSerializer, ChatBotSerializer
from smarter.common.const import (
    SMARTER_CHAT_SESSION_KEY_NAME,
    SMARTER_WAFFLE_REACTAPP_DEBUG_MODE,
    SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING,
)
from smarter.common.exceptions import SmarterExceptionBase, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.request import SmarterRequestHelper
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)


MAX_RETURNED_PLUGINS = 10


logger = logging.getLogger(__name__)


class SmarterChatappViewError(SmarterExceptionBase):
    """Base class for all SmarterChatapp errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Chatapp error"


class SmarterChatSession(SmarterRequestHelper):
    """
    Helper class that provides methods for creating a session key and client key.
    """

    _session_key: str = None
    _chat: Chat = None
    _chatbot: ChatBot = None
    _chat_helper: ChatHelper = None
    _url: str = None

    def __init__(self, request, session_key: str = None, chatbot: ChatBot = None):
        super().__init__(request)

        parsed_url = urllib.parse.urlparse(request.build_absolute_uri())
        # remove any query strings from url and also prune any trailing '/config/' from the url
        clean_url = parsed_url._replace(query="").geturl()
        if clean_url.endswith("/config/"):
            clean_url = clean_url[:-8]
        self._url = clean_url

        try:
            if session_key:
                SmarterValidator.validate_session_key(session_key)
        except SmarterValueError as e:
            logger.error("%s - %s", self.formatted_class_name, e)
            session_key = None

        try:
            self._chat = Chat.objects.get(session_key=session_key, url=self.url)
            self._session_key = session_key
        except Chat.DoesNotExist:
            self._session_key = self.generate_key()
            if session_key:
                logger.warning(
                    "%s - session_key %s not found for url %s. New session key generated %s",
                    self.formatted_class_name,
                    session_key,
                    self.url,
                    self._session_key,
                )

        self._chatbot = chatbot
        self._chat_helper = ChatHelper(session_key=self.session_key, request=request, chatbot=self.chatbot)
        self._chat = self._chat_helper.chat

        if waffle.switch_is_active(SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s - session established: %s", self.formatted_class_name, self.data)

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

    @property
    def url(self):
        return self._url

    @property
    def chatbot(self):
        return self._chatbot

    @property
    def session_key(self):
        return self._session_key

    @property
    def chat(self):
        return self._chat

    @property
    def chat_helper(self):
        return self._chat_helper

    @property
    def unique_client_string(self):
        return f"{self.account.account_number}{self.url}{self.user_agent}{self.ip_address}"

    @property
    def client_key(self):
        return hashlib.sha256(self.unique_client_string.encode()).hexdigest()

    def generate_key(self):
        key_string = self.unique_client_string + str(datetime.now())
        return hashlib.sha256(key_string.encode()).hexdigest()


# pylint: disable=R0902
# @method_decorator(csrf_exempt, name="dispatch")
class ChatConfigView(View, AccountMixin):
    """
    Chat config view for smarter web. This view is protected and requires the user
    to be authenticated. It works with any ChatBots but is aimed at chatbots running
    inside the web console in sandbox mode.

    example: https://sales.3141-5926-5359.alpha.api.smarter.sh/chatbot/config/
    """

    authentication_classes = (SmarterTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    _request_timestamp = datetime.now()
    thing: SmarterJournalThings = None
    command: SmarterJournalCliCommands = None
    _sandbox_mode: bool = True
    session: SmarterChatSession = None
    chatbot_helper: ChatBotHelper = None
    _chatbot: ChatBot = None

    @property
    def request_timestamp(self):
        return self._request_timestamp

    @property
    def chatbot(self):
        return self._chatbot

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            try:
                raise SmarterChatappViewError("Authentication failed.")
            except SmarterChatappViewError as e:
                return SmarterJournaledJsonErrorResponse(
                    request=request, thing=self.manifest_kind, command=None, e=e, status=HTTPStatus.FORBIDDEN
                )

        self._user = request.user
        name = kwargs.pop("name", None)
        self._sandbox_mode = name is not None

        try:
            self._chatbot = ChatBot.objects.get(name=name, account=self.account)
        except ChatBot.DoesNotExist:
            return HttpResponseNotFound(f"Chatbot not found: {name}")

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}
        if waffle.switch_is_active(SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s - data=%s", self.formatted_class_name, data)

        # Initialize the chat session for this request. session_key is generated
        # and managed by the /config/ endpoint for the chatbot
        #
        # example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbots/config/?session_key=123456
        #
        # The React app calls this endpoint at app initialization to get a
        # json dict that includes, among other pertinent info, this session_key
        # which uniquely identifies the device and the individual chatbot session
        # for the device.
        session_key = data.get(SMARTER_CHAT_SESSION_KEY_NAME) or request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME) or None
        self.session = SmarterChatSession(request, session_key=session_key, chatbot=self.chatbot)
        self.chatbot_helper = ChatBotHelper(
            url=self.session.url, user=self.session.user_profile.user, account=self.session.account, name=name
        )
        self._chatbot = self.chatbot_helper.chatbot

        if not self.chatbot:
            return HttpResponseNotFound()

        self.thing = SmarterJournalThings(SmarterJournalThings.CHAT_CONFIG)
        self.command = SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT_CONFIG)
        return super().dispatch(request, *args, **kwargs)

    # pylint: disable=unused-argument
    def post(self, request, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        data = self.config(request=request)
        return SmarterJournaledJsonResponse(request=request, data=data, thing=self.thing, command=self.command)

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        data = self.config(request=request)
        return SmarterJournaledJsonResponse(request=request, data=data, thing=self.thing, command=self.command)

    @property
    def sandbox_mode(self):
        return self._sandbox_mode

    def config(self, request) -> dict:
        """
        React context for all templates that render
        a React app.
        """
        chatbot_serializer = ChatBotSerializer(self.chatbot, context={"request": request}) if self.chatbot else None

        # plugins context. the main thing we need here is to constrain the number of plugins
        # returned to some reasonable number, since we'll probaably have cases where
        # the chatbot has a lot of plugins (hundreds, thousands...).
        chatbot_plugins_count = ChatBotPlugin.objects.filter(chatbot=self.chatbot).count()
        chatbot_plugins = ChatBotPlugin.objects.filter(chatbot=self.chatbot).order_by("-pk")[:MAX_RETURNED_PLUGINS]
        chatbot_plugin_serializer = ChatBotPluginSerializer(chatbot_plugins, many=True)

        retval = {
            "data": {
                SMARTER_CHAT_SESSION_KEY_NAME: self.session.session_key,
                "sandbox_mode": self.sandbox_mode,
                "debug_mode": waffle.switch_is_active(SMARTER_WAFFLE_REACTAPP_DEBUG_MODE),
                "chatbot": chatbot_serializer.data,
                "console": self.session.chat_helper.console,
                "meta_data": self.chatbot_helper.to_json(),
                "history": self.session.chat_helper.chat_history,
                "tool_calls": [],
                "plugins": {
                    "meta_data": {
                        "total_plugins": chatbot_plugins_count,
                        "plugins_returned": len(chatbot_plugins),
                    },
                    "plugins": chatbot_plugin_serializer.data,
                },
            },
        }
        return retval


# @method_decorator(csrf_exempt, name="dispatch")
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
    chatbot_helper: ChatBotHelper = None
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
        self.chatbot_helper = ChatBotHelper(url=self.url, user=self.user_profile.user, account=self.account, name=name)
        self.chatbot = self.chatbot_helper.chatbot
        if not self.chatbot:
            return HttpResponseNotFound()
        return render(request, self.template_path)


class ChatAppListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chatapp list view for smarter web console. This view is protected and
    requires the user to be authenticated. It generates cards for each
    ChatBots.
    """

    template_path = "chatapps/listview.html"
    chatbots: models.QuerySet[ChatBot] = None
    chatbot_helpers: list[ChatBotHelper] = []

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 300:
            return response

        self.chatbot_helpers = []

        def was_already_added(chatbot_helper: ChatBotHelper) -> bool:
            for b in self.chatbot_helpers:
                if b.chatbot.id == chatbot_helper.chatbot.id:
                    return True

        # get all of the smarter demo chatbots
        smarter_admin = smarter_admin_user_profile()
        smarter_demo_chatbots = ChatBot.objects.filter(account=smarter_admin.account)
        for chatbot in smarter_demo_chatbots:
            chatbot_helper = ChatBotHelper(account=smarter_admin.account, name=chatbot.name)
            self.chatbot_helpers.append(chatbot_helper)

        # get all chatbots for the account
        self.chatbots = ChatBot.objects.filter(account=self.account)

        for chatbot in self.chatbots:
            chatbot_helper = ChatBotHelper(account=self.account, name=chatbot.name)
            if not was_already_added(chatbot_helper):
                self.chatbot_helpers.append(chatbot_helper)

        context = {"smarter_admin": smarter_admin, "chatbot_helpers": self.chatbot_helpers}
        return render(request, template_name=self.template_path, context=context)
