"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""

import logging

from django.http import HttpResponseNotFound

from smarter.apps.chatbot.models import ChatBot
from smarter.common.helpers.view_helpers import SmarterAuthenticatedNeverCachedWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class ChatAppView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chat app view for smarter web. This view is protected and requires the user
    to be authenticated. It serves the chat app's main page within the Smarter
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


    ChatBot.get_by_url: This method is used to get the chatbot object by the
    url of the current request. The url is used to determine which chatbot to
    display. The url is expected to be in one of these two formats:
    - http://127.0.0.1:8000/chatapp/<str:name>/
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatapp/
    - https://hr.smarter.querium.com/chatapp/
    We leverage ChatBotApiUrlHelper() to parse the url and get the chatbot object.
    """

    template_path = "index.html"
    chatbot: ChatBot = None

    def get_chatbot_by_name(self, name) -> ChatBot:
        try:
            return ChatBot.objects.get(account=self.account, name=name)
        except ChatBot.DoesNotExist:
            return None

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code < 400:
            name = kwargs.get("name")
            if name:
                self.chatbot = self.get_chatbot_by_name(name)
            else:
                self.chatbot = ChatBot.get_by_url(request.get_host())
            if not self.chatbot:
                return HttpResponseNotFound()
        return response
