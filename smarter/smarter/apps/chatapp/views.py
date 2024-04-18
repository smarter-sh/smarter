"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import logging
from urllib.parse import urljoin

from django.http import HttpResponseNotFound
from django.shortcuts import render

from smarter.apps.chat.models import ChatHistory
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


logger = logging.getLogger(__name__)


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
        host = request.get_host()
        url = SmarterValidator.urlify(host)

        # backend context
        backend_context = {
            "BASE_URL": url,
            "API_URL": urljoin(chatbot.url, "chatbot"),
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
