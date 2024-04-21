"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import logging
import warnings

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.chat.models import ChatHistory
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
from smarter.apps.chatbot.serializers import ChatBotPluginSerializer, ChatBotSerializer
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
    """

    _sandbox_mode: bool = True
    helper: ChatBotHelper = None
    account: Account = None
    user: UserType = None
    user_profile: UserProfile = None
    chatbot: ChatBot = None
    chatbot_serializer: ChatBotSerializer = None
    chatbot_plugin_serializer: ChatBotPluginSerializer = None
    url: str = None

    def dispatch(self, request, *args, **kwargs):
        name = kwargs.pop("name", None)
        self.user = request.user
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.account = self.user_profile.account

        self._sandbox_mode = name is not None
        self.url = request.build_absolute_uri()
        self.helper = ChatBotHelper(url=self.url, user=self.user_profile.user, account=self.account, name=name)
        self.chatbot = self.helper.chatbot
        if not self.chatbot:
            return HttpResponseNotFound()
        self.chatbot_serializer = ChatBotSerializer(self.chatbot)
        chatbot_plugins = ChatBotPlugin.objects.filter(chatbot=self.chatbot)
        self.chatbot_plugin_serializer = ChatBotPluginSerializer(chatbot_plugins, many=True)
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

        # backend context
        backend_context = {
            "BASE_URL": self.url,
            "API_URL": self.chatbot.url_chatbot,
            "SANDBOX_MODE": self.sandbox_mode,
        }

        app_context = {
            "NAME": self.chatbot.app_name or "chatbot",
            "ASSISTANT": self.chatbot.app_assistant or "Smarter",
            "WELCOME_MESSAGE": self.chatbot.app_welcome_message or "Welcome to the chatbot!",
            "EXAMPLE_PROMPTS": self.chatbot.app_example_prompts or [],
            "PLACEHOLDER": self.chatbot.app_placeholder or "Type something here...",
            "INFO_URL": self.chatbot.app_info_url,
            "BACKGROUND_IMAGE_URL": self.chatbot.app_background_image_url,
            "LOGO_URL": self.chatbot.app_logo_url,
            "FILE_ATTACHMENT_BUTTON": self.chatbot.app_file_attachment,
        }

        # chat context
        chat_history = ChatHistory.objects.filter(user=self.user_profile.user).order_by("-created_at").first()
        chat_context = {
            "ID": chat_history.chat_id if chat_history else "undefined",
            "HISTORY": chat_history.messages if chat_history else [],
            "MOST_RECENT_RESPONSE": chat_history.response if chat_history else None,
        }

        # sandbox mode
        sandbox_context = {}
        if self.sandbox_mode:
            plugins = [plugin.name for plugin in ChatBotPlugin.plugins(self.chatbot)]
            sandbox_context = {
                "PLUGINS": plugins,
                "URL": self.chatbot.url,
                "DEFAULT_URL": self.chatbot.default_url,
                "CUSTOM_URL": self.chatbot.custom_url,
                "SANDBOX_URL": self.chatbot.sandbox_url,
                "CREATED_AT": self.chatbot.created_at,
                "UPDATED_AT": self.chatbot.updated_at,
            }

        retval = {
            "CHATBOT": self.chatbot_serializer.data,
            "PLUGINS": self.chatbot_plugin_serializer.data,
            "BACKEND": backend_context,
            "APP": app_context,
            "CHAT": chat_context,
            "SANDBOX": sandbox_context,
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
        chat_history = ChatHistory.objects.filter(user=request.user).order_by("-created_at").first()
        chat_context = {
            "ID": chat_history.chat_id if chat_history else "undefined",
            "HISTORY": chat_history.messages if chat_history else [],
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
