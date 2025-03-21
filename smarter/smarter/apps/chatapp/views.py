"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import logging
from http import HTTPStatus
from urllib.parse import urljoin

import waffle
from django.conf import settings
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator

# from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

# from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication

from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.chat.models import Chat, ChatHelper
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotHelper,
    ChatBotPlugin,
    ChatBotRequests,
    ChatBotRequestsSerializer,
    get_cached_chatbot_by_request,
)
from smarter.apps.chatbot.serializers import ChatBotPluginSerializer, ChatBotSerializer
from smarter.apps.plugin.models import (
    PluginSelectorHistory,
    PluginSelectorHistorySerializer,
)
from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME, SmarterWaffleSwitches
from smarter.common.exceptions import SmarterExceptionBase, SmarterValueError
from smarter.common.helpers.url_helpers import clean_url
from smarter.lib.cache import cache_results
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.views.error import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)


# from rest_framework.permissions import IsAuthenticated


MAX_RETURNED_PLUGINS = 10


logger = logging.getLogger(__name__)


class SmarterChatappViewError(SmarterExceptionBase):
    """Base class for all SmarterChatapp errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Chatapp error"


class SmarterChatSession(SmarterRequestMixin, SmarterHelperMixin):
    """
    Helper class that provides methods for creating a session key and client key.
    """

    _chat: Chat = None
    _chat_helper: ChatHelper = None
    _chatbot: ChatBot = None

    def __init__(self, request, chatbot: ChatBot = None):
        SmarterRequestMixin.__init__(self, request=request)
        SmarterHelperMixin.__init__(self)

        self._url = self.clean_url(request.build_absolute_uri())

        if chatbot:
            self._chatbot = chatbot
            self.account = chatbot.account

        # leaving this in place as a reminder that we need one or the other
        if not self.session_key and not self.chatbot:
            raise SmarterChatappViewError("Either a session_key or a chatbot instance is required")

        self._chat_helper = ChatHelper(request=request, session_key=self.session_key, chatbot=self.chatbot)
        self._chat = self._chat_helper.chat

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info("%s - session established: %s", self.formatted_class_name, self.session_key)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"{self.__class__.__name__}(session_key={self.session_key}, chatbot={self.chatbot})"

    @property
    def chatbot(self):
        return self._chatbot

    @property
    def chat(self):
        return self._chat

    @property
    def chat_helper(self):
        return self._chat_helper

    def clean_url(self, url: str) -> str:
        """
        Clean the url of any query strings and trailing '/config/' strings.
        """
        retval = clean_url(url)
        if retval.endswith("/config/"):
            retval = retval[:-8]
        return retval


# pylint: disable=R0902
@method_decorator(csrf_exempt, name="dispatch")
class ChatConfigView(View, SmarterRequestMixin, SmarterHelperMixin):
    """
    Chat config view for smarter web. This view is protected and requires the user
    to be authenticated. It works with any ChatBots but is aimed at chatbots running
    inside the web console in sandbox mode.

    example: https://smarter.3141-5926-5359.alpha.api.smarter.sh/config/
    """

    authentication_classes = (SmarterTokenAuthentication, SessionAuthentication)
    # permission_classes = (IsAuthenticated,)

    thing: SmarterJournalThings = None
    command: SmarterJournalCliCommands = None
    session: SmarterChatSession = None
    _chatbot_helper: ChatBotHelper = None
    _chatbot: ChatBot = None

    @property
    def chatbot(self):
        return self._chatbot

    @property
    def chatbot_helper(self) -> ChatBotHelper:
        if self._chatbot_helper:
            return self._chatbot_helper
        if self.chatbot:
            # throw everything but the kitchen sink at the ChatBotHelper
            self._chatbot_helper = ChatBotHelper(
                request=self.request, name=self._chatbot.name, chatbot_id=self._chatbot.id
            )
        else:
            self._chatbot_helper = ChatBotHelper(request=self.request)
        return self._chatbot_helper

    @chatbot_helper.setter
    def chatbot_helper(self, value: ChatBotHelper):
        self._chatbot_helper = value
        if self._chatbot_helper:
            self._chatbot = self.chatbot_helper.chatbot
            self.account = self.chatbot_helper.account
            logger.info("%s - chatbot_helper() setter chatbot=%s", self.formatted_class_name, self.chatbot)
        else:
            self._chatbot = None
            logger.info("%s - chatbot_helper() setter chatbot is unset", self.formatted_class_name)

    def dispatch(self, request, *args, chatbot_id: int = None, **kwargs):
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)
        logger.info("%s - dispatch() url=%s session=%s", self.formatted_class_name, self.url, self.session)
        name = kwargs.pop("name", None)
        logger.warning("%s authentication is disabled for this view.", self.formatted_class_name)

        try:
            self._chatbot = get_cached_chatbot_by_request(request=request)
            if not self._chatbot:
                self.chatbot_helper = ChatBotHelper(request=request, chatbot_id=chatbot_id, name=name)
        except ChatBot.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=HTTPStatus.NOT_FOUND.value)

        if self.chatbot_helper and self.chatbot_helper.is_authentication_required and not request.user.is_authenticated:
            try:
                raise SmarterChatappViewError(
                    "Authentication failed. Are you logged in? Smarter sessions automatically expire after 24 hours."
                )
            except SmarterChatappViewError as e:
                return SmarterJournaledJsonErrorResponse(
                    request=request,
                    thing=SmarterJournalThings.CHAT_CONFIG,
                    command=None,
                    e=e,
                    status=HTTPStatus.FORBIDDEN.value,
                )

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info(
                "%s - chatbot=%s - chatbot_helper=%s", self.formatted_class_name, self.chatbot, self.chatbot_helper
            )

        # Initialize the chat session for this request. session_key is generated
        # and managed by the /config/ endpoint for the chatbot
        #
        # example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbots/config/?session_key=123456
        #
        # The React app calls this endpoint at app initialization to get a
        # json dict that includes, among other pertinent info, this session_key
        # which uniquely identifies the device and the individual chatbot session
        # for the device.
        self.session = SmarterChatSession(request, chatbot=self.chatbot)

        if not self.chatbot:
            return JsonResponse({"error": "Not found"}, status=HTTPStatus.NOT_FOUND.value)

        self.thing = SmarterJournalThings(SmarterJournalThings.CHAT_CONFIG)
        self.command = SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT_CONFIG)
        return super().dispatch(request, *args, **kwargs)

    # pylint: disable=unused-argument
    def post(self, request, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        logger.info("%s - post()", self.formatted_class_name)
        data = self.config(request=request)
        return SmarterJournaledJsonResponse(request=request, data=data, thing=self.thing, command=self.command)

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        logger.info("%s - get()", self.formatted_class_name)
        data = self.config(request=request)
        return SmarterJournaledJsonResponse(request=request, data=data, thing=self.thing, command=self.command)

    def clean_url(self, url: str) -> str:
        """
        Clean the url of any query strings and trailing '/config/' strings.
        """
        retval = clean_url(url)
        if retval.endswith("/config/"):
            retval = retval[:-8]
        return retval

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
        history = self.session.chat_helper.history

        # add chatbot_request_history and plugin_selector_history to history
        # these have to be added here due to circular import issues.
        chatbot_requests_queryset = ChatBotRequests.objects.filter(session_key=self.session.session_key).order_by("-id")
        chatbot_requests_serializer = ChatBotRequestsSerializer(chatbot_requests_queryset, many=True)
        history["chatbot_request_history"] = chatbot_requests_serializer.data

        plugin_selector_history_queryset = PluginSelectorHistory.objects.filter(session_key=self.session.session_key)
        plugin_selector_history_serializer = PluginSelectorHistorySerializer(
            plugin_selector_history_queryset, many=True
        )
        history["plugin_selector_history"] = plugin_selector_history_serializer.data

        retval = {
            "data": {
                SMARTER_CHAT_SESSION_KEY_NAME: self.session.session_key,
                "sandbox_mode": self.chatbot_helper.is_chatbot_sandbox_url,
                "debug_mode": waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_REACTAPP_DEBUG_MODE),
                "chatbot": chatbot_serializer.data,
                "history": history,
                "meta_data": self.chatbot_helper.to_json(),
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


class ChatAppWorkbenchView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chat app view for smarter web. This view is protected and requires the user
    to be authenticated. It works with deployed and not-yet-deployed ChatBots.
    The url is expected to be in one of three formats.

    Sandbox mode:
    - http://smarter.querium.com/chatapp/hr/
    - http://127.0.0.1:8000/chatapp/<str:name>/

    Production mode:
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatapp/

    It serves the chat app's main page within the Smarter
    dashboard web app. React builds are served from an AWS Cloudfront CDN
    such as https://cdn.platform.smarter.sh/ui-chat/index.html, which
    returns an html snippet containing reactjs build artifacts such as:

        <script type="module" crossorigin src="https://cdn.platform.smarter.sh/ui-chat/assets/main-BNT0OHb-.js"></script>
        <link rel="stylesheet" crossorigin href="https://cdn.platform.smarter.sh/ui-chat/assets/main-D14Wl0PM.css">

    Our Django template will inject this html snippet into the DOM, and
    the React app will take over from there.

    Cache behavior:
    We probably don't need to worry about cache behavior.
    Nonetheless, we're using the `never_cache` decorator to
    ensure that the browser doesn't cache the page itself, which could cause
    problems if the user logs out and then logs back in without refreshing the
    page.
    """

    template_path = "chatapp/workbench.html"

    # The React app originates from
    #  - https://github.com/smarter-sh/smarter-chat and
    #  - https://github.com/smarter-sh/smarter-workbench
    # and is built-deployed to AWS Cloudfront. The React app is loaded from
    # a url like: https://cdn.alpha.platform.smarter.sh/ui-chat/index.html
    reactjs_cdn_path = "/ui-chat/app-loader.js"
    reactjs_loader_url = urljoin(smarter_settings.environment_cdn_url, reactjs_cdn_path)

    # start with a string like: "smarter.sh/v1/ui-chat/root"
    # then convert it into an html safe id like: "smarter-sh-v1-ui-chat-root"
    div_root_id = SmarterApiVersions.V1 + reactjs_cdn_path.replace("app-loader.js", "root")
    div_root_id = div_root_id.replace(".", "-").replace("/", "-")

    chatbot: ChatBot = None
    chatbot_helper: ChatBotHelper = None
    url: str = None

    def dispatch(self, request, *args, **kwargs):
        name = kwargs.pop("name", None)
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 300:
            return response
        self.url = request.build_absolute_uri()

        try:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_REACTAPP_DEBUG_MODE):
                logger.info(
                    "%s - url=%s, account=%s, user=%s, name=%s",
                    self.formatted_class_name,
                    self.url,
                    self.account,
                    self.user_profile.user,
                    name,
                )
            self.chatbot = get_cached_chatbot_by_request(request=request)
            if not self.chatbot:
                self.chatbot_helper = ChatBotHelper(request=request, name=name)
                self.chatbot = self.chatbot_helper.chatbot if self.chatbot_helper.chatbot else None
            if not self.chatbot:
                raise ChatBot.DoesNotExist
        except ChatBot.DoesNotExist:
            return SmarterHttpResponseNotFound(request=request, error_message="ChatBot not found")
        # pylint: disable=broad-except
        except Exception as e:
            return SmarterHttpResponseServerError(request=request, error_message=str(e))

        # the basic idea is to pass the names of the necessary cookies to the React app, and then
        # it is supposed to find and read the cookies to get the chat session key, csrf token, etc.
        context = {
            "div_id": self.div_root_id,
            "app_loader_url": self.reactjs_loader_url,
            "chatbot_api_url": self.chatbot.url,
            "toggle_metadata": True,
            "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
            "smarter_session_cookie_name": SMARTER_CHAT_SESSION_KEY_NAME,  # this is the Smarter chat session, not the Django session.
            "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
            "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
            "debug_mode": waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_REACTAPP_DEBUG_MODE),
        }
        return render(request=request, template_name=self.template_path, context=context)


class ChatAppListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chatapp list view for smarter web console. This view is protected and
    requires the user to be authenticated. It generates cards for each
    ChatBots.
    """

    template_path = "chatbot/listview.html"
    chatbots: models.QuerySet[ChatBot] = None
    chatbot_helpers: list[ChatBotHelper] = []

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 300:
            return response

        self.chatbot_helpers = []

        def was_already_added(chatbot_helper: ChatBotHelper) -> bool:
            if not chatbot_helper.chatbot:
                raise SmarterValueError("chatbot_helper.chatbot is not set")
            for b in self.chatbot_helpers:
                if b.chatbot and b.chatbot.id == chatbot_helper.chatbot.id:
                    return True
            return

        @cache_results()
        def get_chatbots_for_account(account) -> list[ChatBot]:
            return ChatBot.objects.filter(account=account)

        self.chatbots = get_chatbots_for_account(account=self.account)

        for chatbot in self.chatbots:
            logger.info("%s - adding chatbot=%s", self.formatted_class_name, chatbot)
            chatbot_helper = ChatBotHelper(chatbot_id=chatbot.id)
            if not was_already_added(chatbot_helper):
                self.chatbot_helpers.append(chatbot_helper)

        smarter_admin = get_cached_smarter_admin_user_profile()
        context = {"smarter_admin": smarter_admin, "chatbot_helpers": self.chatbot_helpers}
        return render(request, template_name=self.template_path, context=context)
