"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import hashlib
import json
import logging
import warnings
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.chat.api.v0.serializers import (
    ChatHistorySerializer,
    ChatPluginUsageSerializer,
    ChatToolCallSerializer,
)
from smarter.apps.chat.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from smarter.apps.chatbot.api.v0.serializers import (
    ChatBotPluginSerializer,
    ChatBotSerializer,
)
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
from smarter.lib.django.user import UserType
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


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
    def get(self, request, *args, **kwargs):
        """
        Get the chatbot configuration.
        """
        if not self.chatbot:
            return HttpResponseNotFound()
        return JsonResponse(data=self.config())

    @property
    def sandbox_mode(self):
        return self._sandbox_mode

    def config(self) -> dict:
        """
        React context for all templates that render
        a React app.
        """
        chat: Chat = None
        chat_history_serializer: ChatHistorySerializer = None
        chat_tool_call_serializer: ChatToolCallSerializer = None
        chat_plugin_usage_serializer: ChatPluginUsageSerializer = None

        # chatbot context
        chatbot_serializer = ChatBotSerializer(self.chatbot) if self.chatbot else None

        # plugins context. the main thing we need here is to constrain the number of plugins
        # returned to some reasonable number, since we'll probaably have cases where
        # the chatbot has a lot of plugins (hundreds, thousands...).
        MAX_PLUGINS = 10
        chatbot_plugins_count = ChatBotPlugin.objects.filter(chatbot=self.chatbot).count()
        chatbot_plugins = ChatBotPlugin.objects.order_by("-pk")[:MAX_PLUGINS]
        chatbot_plugin_serializer = ChatBotPluginSerializer(chatbot_plugins, many=True)

        # message thread history context
        chat, created = Chat.objects.get_or_create(
            session_key=self.session_key,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            url=self.url,
        )
        if not created:
            chat_history = ChatHistory.objects.get(chat=chat) if chat else None
            chat_history_serializer = ChatHistorySerializer(chat_history) if chat_history else None

            chat_tool_call = ChatToolCall.objects.get(chat=chat) if chat else None
            chat_tool_call_serializer = ChatToolCallSerializer(chat_tool_call) if chat_tool_call else None

            chat_plugin_usage = ChatPluginUsage.objects.get(chat=chat) if chat else None
            chat_plugin_usage_serializer = ChatPluginUsageSerializer(chat_plugin_usage) if chat_plugin_usage else None

        retval = {
            "session_key": self.session_key,
            "sandbox_mode": self.sandbox_mode,
            "chatbot": chatbot_serializer.data,
            "plugins": {
                "meta_data": {
                    "total_plugins": chatbot_plugins_count,
                    "plugins_returned": len(chatbot_plugins),
                },
                "plugins": chatbot_plugin_serializer.data,
            },
            "meta_data": self.helper.to_json(),
            "chat": {
                "id": chat.id if chat else None,
                "history": chat_history_serializer.data if chat_history_serializer else [],
                "tool_calls": chat_tool_call_serializer.data if chat_tool_call_serializer else [],
                "plugin_usage": chat_plugin_usage_serializer.data if chat_plugin_usage_serializer else [],
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

    @property
    def sandbox_mode(self):
        return self._sandbox_mode

    def get_chatbot_by_name(self, name) -> ChatBot:
        try:
            return ChatBot.objects.get(account=self.account, name=name)
        except ChatBot.DoesNotExist:
            return None

    def get_chatbot_by_url(self, url) -> ChatBot:
        return ChatBot.get_by_url(url)

    def react_context(self, request, chatbot: ChatBot):
        """
        React context for all templates that render
        a React app.
        """
        warnings.warn(
            "The 'react_context' method is deprecated. Use api endpoint /chatapp/<name>/config/", DeprecationWarning
        )

        url = request.build_absolute_uri()

        # backend context
        backend_context = {
            "BASE_URL": url,
            "API_URL": chatbot.url_chatbot,
            "SANDBOX_MODE": self.sandbox_mode,
        }

        app_context = {
            "NAME": chatbot.app_name or "chatbot",
            "ASSISTANT": chatbot.app_assistant or "Smarter",
            "WELCOME_MESSAGE": chatbot.app_welcome_message or "Welcome to the chatbot!",
            "EXAMPLE_PROMPTS": chatbot.app_example_prompts or [],
            "PLACEHOLDER": chatbot.app_placeholder or "Type something here...",
            "INFO_URL": chatbot.app_info_url,
            "BACKGROUND_IMAGE_URL": chatbot.app_background_image_url,
            "LOGO_URL": chatbot.app_logo_url,
            "FILE_ATTACHMENT_BUTTON": chatbot.app_file_attachment,
        }

        # chat context
        chat_history = ChatHistory.objects.filter().order_by("-created_at").first()
        messages = chat_history.request["messages"] if chat_history else []
        chat_context = {
            "ID": chat_history.id if chat_history else None,
            "HISTORY": messages,
            "MOST_RECENT_RESPONSE": chat_history.response if chat_history else None,
        }

        # sandbox mode
        sandbox_context = {}
        if self.sandbox_mode:
            plugins = [plugin.name for plugin in ChatBotPlugin.plugins(chatbot)]
            sandbox_context = {
                "CHATBOT_ID": chatbot.id,
                "CHATBOT_NAME": chatbot.name,
                "PLUGINS": plugins,
                "URL": chatbot.url,
                "DEFAULT_URL": chatbot.default_url,
                "CUSTOM_URL": chatbot.custom_url,
                "SANDBOX_URL": chatbot.sandbox_url,
                "CREATED_AT": chatbot.created_at,
                "UPDATED_AT": chatbot.updated_at,
            }

        retval = {
            "react": True,
            "react_config": {
                "BACKEND": backend_context,
                "APP": app_context,
                "CHAT": chat_context,
                "SANDBOX": sandbox_context,
            },
        }
        logger.debug("react_context(): %s", retval)
        return retval

    def react_render(self, request):
        context = self.react_context(request, self.chatbot)
        return render(request, self.template_path, context=context)

    def dispatch(self, request, *args, **kwargs):
        name = kwargs.pop("name", None)
        self._sandbox_mode = name is not None
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 300:
            return response
        if name:
            self.chatbot = self.get_chatbot_by_name(name)
        if not self.chatbot:
            self.chatbot = self.get_chatbot_by_url(request.get_host())
        if not self.chatbot:
            return HttpResponseNotFound()
        return self.react_render(request)
