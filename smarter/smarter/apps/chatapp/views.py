# -*- coding: utf-8 -*-
"""
Views for the React chat app. See doc/DJANGO-REACT-INTEGRATION.md for more
information about how the React app is integrated into the Django app.
"""
from django.shortcuts import get_object_or_404

from smarter.apps.chatbot.models import ChatBot
from smarter.common.view_helpers import SmarterAuthenticatedNeverCachedWebView


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
    """

    chatbot: ChatBot = None

    def dispatch(self, request, *args, **kwargs):

        # setting this less for its functionality than for using it as a way
        # to validate the hostname and that the chatbot actually exists.
        self.chatbot = get_object_or_404(ChatBot, hostname=request.get_host())
        response = super().dispatch(request, *args, **kwargs)
        return response

    template_path = "index.html"
