# pylint: disable=W0613
"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import logging
import traceback
from http import HTTPStatus
from typing import Optional
from urllib.parse import urljoin

from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotHelper,
    ChatBotPlugin,
    ChatBotRequests,
    ChatBotRequestsSerializer,
    get_cached_chatbot_by_request,
)
from smarter.apps.chatbot.serializers import (
    ChatBotConfigSerializer,
    ChatBotPluginSerializer,
)
from smarter.apps.plugin.models import (
    PluginSelectorHistory,
    PluginSelectorHistorySerializer,
)
from smarter.apps.prompt.models import Chat, ChatHelper
from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterException, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_json
from smarter.common.helpers.url_helpers import clean_url
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.view_helpers import (
    SmarterAuthenticatedNeverCachedWebView,
    SmarterNeverCachedWebView,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.view_helpers import UnauthenticatedPermissionClass
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)

from .signals import chat_config_invoked, chat_session_invoked


MAX_RETURNED_PLUGINS = 10


logger = logging.getLogger(__name__)


class SmarterChatappViewError(SmarterException):
    """Base class for all SmarterChatapp errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Chatapp error"


class SmarterChatSession(SmarterHelperMixin):
    """
    Helper class that provides methods for creating a session key and client key.
    """

    _chat: Optional[Chat] = None
    _chat_helper: Optional[ChatHelper] = None
    _chatbot: Optional[ChatBot] = None
    request: Optional[HttpRequest] = None
    session_key: Optional[str] = None

    def __init__(
        self, request: HttpRequest, session_key: Optional[str], *args, chatbot: Optional[ChatBot] = None, **kwargs
    ):
        logger.info("SmarterChatSession().__init__() called with session_key=%s, chatbot=%s", session_key, chatbot)
        self.request = request
        self.session_key = session_key

        if chatbot:
            self._chatbot = chatbot
            self.account = chatbot.account

        # leaving this in place as a reminder that we need one or the other
        if not self.session_key and not self.chatbot:
            raise SmarterChatappViewError(
                f"Either a session_key or a chatbot instance is required. url={request.build_absolute_uri()}"
            )

        self._chat_helper = ChatHelper(request, *args, session_key=self.session_key, chatbot=self.chatbot, **kwargs)
        self._chat = self._chat_helper.chat

        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            logger.info("%s - session established: %s", self.formatted_class_name, self.session_key)

        chat_session_invoked.send(sender=self.__class__, instance=self, request=request)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"{self.__class__.__name__}(chatbot={self.chatbot}, session_key={self.session_key})"

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
class ChatConfigView(SmarterNeverCachedWebView):
    """
    Chat config view for smarter web. This view is protected and requires the user
    to be authenticated. It works with any ChatBot instance but is aimed at chatbots
    instances running inside the web console in sandbox mode.

    example: https://smarter.3141-5926-5359.alpha.api.smarter.sh/config/
    """

    authentication_classes = None
    permission_classes = (UnauthenticatedPermissionClass,)

    thing: Optional[SmarterJournalThings] = None
    command: Optional[SmarterJournalCliCommands] = None
    session: Optional[SmarterChatSession] = None
    chatbot_name: Optional[str] = None
    _chatbot_helper: Optional[ChatBotHelper] = None
    _chatbot: Optional[ChatBot] = None

    @property
    def chatbot(self) -> Optional[ChatBot]:
        return self._chatbot

    @property
    def chatbot_helper(self) -> Optional[ChatBotHelper]:
        if self._chatbot_helper:
            return self._chatbot_helper
        if self.chatbot:
            # throw everything but the kitchen sink at the ChatBotHelper
            self._chatbot_helper = ChatBotHelper(
                request=self.smarter_request,
                session_key=self.session.session_key if self.session else None,
                name=self._chatbot.name if self._chatbot else self.chatbot_name,
                chatbot_id=self._chatbot.id if self._chatbot else None,  # type: ignore[union-attr]
                account=self.account,
                user=self.user,
                user_profile=self.user_profile,
            )
        else:
            self._chatbot_helper = ChatBotHelper(
                request=self.smarter_request,
                name=self.chatbot_name or self.smarter_request_chatbot_name,
                session_key=self.session.session_key if self.session else None,
                account=self.account,
                user=self.user,
                user_profile=self.user_profile,
            )
        return self._chatbot_helper

    @chatbot_helper.setter
    def chatbot_helper(self, value: Optional[ChatBotHelper]):
        self._chatbot_helper = value
        if self._chatbot_helper and self._chatbot_helper.chatbot:
            self._chatbot = self._chatbot_helper.chatbot
            self.account = self._chatbot_helper.account
            self.user = self._chatbot_helper.user
            self.user_profile = self._chatbot_helper.user_profile
            if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
                logger.info("%s - chatbot_helper() setter chatbot=%s", self.formatted_class_name, self.chatbot)
        else:
            self._chatbot = None
            if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
                logger.info("%s - chatbot_helper() setter chatbot is unset", self.formatted_class_name)

    def dispatch(self, request: HttpRequest, *args, chatbot_id: Optional[int] = None, **kwargs):

        if self.user_profile is not None:
            logger.info(
                "%s.dispatch() - %s user_profile=%s",
                self.formatted_class_name,
                request.build_absolute_uri(),
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.dispatch() - %s user_profile is None. This may cause issues with the chat config view.",
                self.formatted_class_name,
                request.build_absolute_uri(),
            )

        # if not request.user.is_authenticated:
        #     return SmarterHttpResponseNotFound(request=request, error_message="ChatBot not found")

        self.chatbot_name = kwargs.get("name", None)
        session_key = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME, None)

        logger.info(
            "%s.dispatch() called with request=%s, chatbot_id=%s, session_key=%s chatbot_name=%s user_profile=%s",
            self.formatted_class_name,
            request.build_absolute_uri(),
            chatbot_id,
            session_key,
            self.chatbot_name,
            self.user_profile,
        )

        try:
            self._chatbot = get_cached_chatbot_by_request(request=request)
            if not self._chatbot:
                logger.info(
                    "%s.dispatch() - attempting to instantiate ChatBotHelper with additional info",
                    self.formatted_class_name,
                )
                self.chatbot_helper = ChatBotHelper(
                    request=self.smarter_request,
                    session_key=session_key,
                    chatbot_id=chatbot_id,
                    name=self.chatbot_name,
                    account=self.account,
                    user=self.user,
                    user_profile=self.user_profile,
                )
        except ChatBot.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=HTTPStatus.NOT_FOUND.value)

        # Initialize the chat session for this request. session_key is generated
        # and managed by the /config/ endpoint for the chatbot
        #
        # example: https://customer-support.3141-5926-5359.api.smarter.sh/workbench/config/?session_key=123456
        #
        # The React app calls this endpoint at app initialization to get a
        # json dict that includes, among other pertinent info, this session_key
        # which uniquely identifies the device and the individual chatbot session
        # for the device.
        self.session = SmarterChatSession(request, session_key=self.session_key, chatbot=self.chatbot)
        session_key = self.session.session_key or self.session_key
        if session_key != self.session_key and session_key is not None:
            logger.info("%s.dispatch() modifying session_key to %s", self.formatted_class_name, session_key)
            self.session_key = session_key
        logger.info(
            "%s.dispatch() received url=%s session_key=%s, name=%s",
            self.formatted_class_name,
            self.url,
            self.session_key,
            self.chatbot_name,
        )

        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            logger.info("%s - dispatch() url=%s session=%s", self.formatted_class_name, self.url, self.session)
        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            logger.warning("%s authentication is disabled for this view.", self.formatted_class_name)

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
                    stack_trace=traceback.format_exc(),
                )

        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            logger.info(
                "%s - chatbot=%s - chatbot_helper=%s", self.formatted_class_name, self.chatbot, self.chatbot_helper
            )

        if not self.chatbot:
            return JsonResponse({"error": "Not found"}, status=HTTPStatus.NOT_FOUND.value)

        self.thing = SmarterJournalThings(SmarterJournalThings.CHAT_CONFIG)
        self.command = SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT_CONFIG)

        logger.info(
            "%s.dispatch() completed with chatbot=%s, session_key=%s",
            self.formatted_class_name,
            self.chatbot,
            self.session.session_key if self.session else "(Missing session)",
        )
        return super().dispatch(request, *args, **kwargs)

    def __str__(self):
        return str(self.chatbot) if self.chatbot else "ChatConfigView"

    # pylint: disable=unused-argument
    def post(self, request: HttpRequest, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            logger.info("%s - post()", self.formatted_class_name)
        data = self.config()
        return SmarterJournaledJsonResponse(request=request, data=data, thing=self.thing, command=self.command)

    # pylint: disable=unused-argument
    def get(self, request: HttpRequest, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            logger.info("%s - get()", self.formatted_class_name)
        data = self.config()
        return SmarterJournaledJsonResponse(request=request, data=data, thing=self.thing, command=self.command)

    def clean_url(self, url: str) -> str:
        """
        Clean the url of any query strings and trailing '/config/' strings.
        """
        retval = clean_url(url)
        if retval.endswith("/config/"):
            retval = retval[:-8]
        return retval

    def config(self) -> dict:
        """
        React context for all templates that render
        a React app.
        """
        # add chatbot_request_history and plugin_selector_history to history
        # these have to be added here due to circular import issues.
        if self.session is None:
            raise SmarterValueError("Session is not set. Cannot retrieve chatbot request history.")
        if self.chatbot_helper is None:
            raise SmarterValueError("ChatBotHelper is not set. Cannot retrieve chatbot request history.")

        chatbot_serializer = (
            ChatBotConfigSerializer(self.chatbot, context={"request": self.smarter_request}) if self.chatbot else None
        )

        # plugins context. the main thing we need here is to constrain the number of plugins
        # returned to some reasonable number, since we'll probaably have cases where
        # the chatbot has a lot of plugins (hundreds, thousands...).
        chatbot_plugins_count = ChatBotPlugin.objects.filter(chatbot=self.chatbot).count()
        chatbot_plugins = ChatBotPlugin.objects.filter(chatbot=self.chatbot).order_by("-pk")[:MAX_RETURNED_PLUGINS]
        chatbot_plugin_serializer = ChatBotPluginSerializer(chatbot_plugins, many=True)
        history = self.session.chat_helper.history if self.session.chat_helper else {}

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
                "debug_mode": waffle.switch_is_active(SmarterWaffleSwitches.REACTAPP_DEBUG_MODE),
                "chatbot": chatbot_serializer.data if chatbot_serializer else None,
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
        chat_config_invoked.send(sender=self.__class__, instance=self, request=self.smarter_request, data=retval)
        return retval


@method_decorator(csrf_exempt, name="dispatch")
class ChatAppWorkbenchView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chat app view for smarter web. This view is protected and requires the user
    to be authenticated. It works with deployed and not-yet-deployed ChatBots.
    The url is expected to be in one of three formats.

    Sandbox mode:
    - http://smarter.querium.com/workbench/hr/
    - http://127.0.0.1:8000/workbench/<str:name>/

    Production mode:
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/workbench/

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

    template_path = "prompt/workbench.html"

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

    chatbot: Optional[ChatBot] = None
    chatbot_helper: Optional[ChatBotHelper] = None

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Dispatch method to handle the request.
        """
        retval = super().dispatch(request, *args, **kwargs)
        if retval.status_code >= 400:
            return retval
        name = kwargs.pop("name", None)
        session_key = kwargs.pop(SMARTER_CHAT_SESSION_KEY_NAME, None)
        if self.user_profile is None:
            raise SmarterValueError("User profile is not set. Cannot proceed with ChatAppWorkbenchView dispatch.")
        if session_key:
            self.session_key = session_key

        try:
            if waffle.switch_is_active(SmarterWaffleSwitches.REACTAPP_DEBUG_MODE) or waffle.switch_is_active(
                SmarterWaffleSwitches.CHATBOT_LOGGING
            ):
                logger.info(
                    "%s - url=%s, account=%s, user=%s, name=%s",
                    self.formatted_class_name,
                    self.url,
                    self.account,
                    self.user_profile.user,
                    name,
                )
            self.chatbot = get_cached_chatbot_by_request(request=self.smarter_request)
            if not self.chatbot:
                self.chatbot_helper = ChatBotHelper(
                    request=self.smarter_request,
                    session_key=self.session_key,
                    name=name,
                    account=self.account,
                    user=self.user,
                    user_profile=self.user_profile,
                )
                self.chatbot = self.chatbot_helper.chatbot if self.chatbot_helper.chatbot else None
            if self.chatbot:
                logger.info(
                    "%s.dispatch() - set chatbot=%s from self.chatbot_helper", self.formatted_class_name, self.chatbot
                )
            else:
                raise ChatBot.DoesNotExist
        except ChatBot.DoesNotExist:
            return SmarterHttpResponseNotFound(request=request, error_message="ChatBot not found")
        # pylint: disable=broad-except
        except Exception as e:
            return SmarterHttpResponseServerError(request=request, error_message=str(e))

        if not self.chatbot:
            return SmarterHttpResponseNotFound(request=request, error_message="ChatBot not found")

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
            "debug_mode": waffle.switch_is_active(SmarterWaffleSwitches.REACTAPP_DEBUG_MODE),
        }
        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            logger.info(
                "%s.dispatch() - rendering template %s with context: %s",
                self.formatted_class_name,
                self.template_path,
                formatted_json(context),
            )
        return render(request=request, template_name=self.template_path, context=context)


class PromptListView(SmarterAuthenticatedNeverCachedWebView):
    """
    list view for smarter workbench web console. This view is protected and
    requires the user to be authenticated. It generates cards for each
    ChatBots.
    """

    template_path = "prompt/listview.html"
    chatbots: Optional[models.QuerySet[ChatBot]] = None
    chatbot_helpers: list[ChatBotHelper] = []

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 300:
            return response

        self.chatbot_helpers = []

        def was_already_added(chatbot_helper: ChatBotHelper) -> bool:
            if not chatbot_helper.chatbot:
                raise SmarterValueError("chatbot_helper.chatbot is not set")
            for b in self.chatbot_helpers:
                if b.chatbot and b.chatbot.id == chatbot_helper.chatbot.id:  # type: ignore[union-attr]
                    return True
            return False

        @cache_results()
        def get_chatbots_for_account(account) -> QuerySet:
            return ChatBot.objects.filter(account=account)

        self.chatbots = get_chatbots_for_account(account=self.account)

        for chatbot in self.chatbots:
            chatbot_helper = ChatBotHelper(
                request=self.smarter_request,
                chatbot_id=chatbot.id,  # type: ignore[union-attr]
                user=self.user,
                account=self.account,
                user_profile=self.user_profile,
            )
            if not was_already_added(chatbot_helper):
                self.chatbot_helpers.append(chatbot_helper)

        smarter_admin = get_cached_smarter_admin_user_profile()
        context = {"smarter_admin": smarter_admin, "chatbot_helpers": self.chatbot_helpers}
        return render(request, template_name=self.template_path, context=context)
