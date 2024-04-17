"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import logging

from django.http import HttpResponseNotFound
from django.shortcuts import render

from smarter.apps.chat.models import ChatHistory
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


logger = logging.getLogger(__name__)


class ChatAppBaseView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chat app sandbox view for smarter web app. Works with pre-production
    chatbots. This view is protected and requires the user to be authenticated.

    The url is expected to be in this format:
    - http://127.0.0.1:8000/chatapp/<str:name>/
    """

    template_path = "index.html"
    chatbot: ChatBot = None

    def get_chatbot_by_name(self, name) -> ChatBot:
        try:
            return ChatBot.objects.get(account=self.account, name=name)
        except ChatBot.DoesNotExist:
            return None

    def get_chatbot_by_url(self, url) -> ChatBot:
        return ChatBot.get_by_url(url)

    def react_context(self, request, chatbot: ChatBot):
        """
        React context processor for all templates that render
        a React app.
        """

        chat_history = ChatHistory.objects.filter(user=request.user).order_by("-created_at").first()
        chat_id = chat_history.chat_id if chat_history else "undefined"
        messages = chat_history.messages if chat_history else []
        most_recent_response = chat_history.response if chat_history else None

        base_url = SmarterValidator.urlify(request.get_host())
        plugins = [plugin.name for plugin in ChatBotPlugin.plugins(chatbot)]

        context_prefix = "BACKEND_"
        return {
            "react": True,
            "react_config": {
                context_prefix + "BASE_URL": base_url,
                context_prefix + "API_URL": chatbot.url,
                context_prefix + "CHATBOT_NAME": chatbot.name,
                context_prefix + "CHATBOT_PLUGINS": plugins,
                context_prefix + "CHAT_ID": chat_id,
                context_prefix + "CHAT_HISTORY": messages,
                context_prefix + "CHAT_MOST_RECENT_RESPONSE": most_recent_response,
            },
        }

    def react_render(self, request):
        context = self.react_context(request, self.chatbot)
        return render(request, self.template_path, context=context)


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class ChatAppView(ChatAppBaseView):
    """
    Chat app view for smarter web. This view is protected and requires the user
    to be authenticated. It works with deployed ChatBots. The url is expected to
    be in one of three formats.

    Sandbox mode:
    - http://smarter.querium.com/chatapp/hr/

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

    def dispatch(self, request, *args, **kwargs):
        name = kwargs.pop("name", None)
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 400:
            return response
        if name:
            self.chatbot = self.get_chatbot_by_name(name)
        if not self.chatbot:
            self.chatbot = self.get_chatbot_by_url(request.get_host())
        if not self.chatbot:
            return HttpResponseNotFound()
        return self.react_render(request)
