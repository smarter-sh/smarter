"""
URLs for Smarter deployed Chatbots.
"""

from django.contrib import admin
from django.urls import include, path

from smarter.apps.chatbot.api.v1.views.default import DefaultChatbotApiView
from smarter.apps.prompt.views import ChatConfigView


urlpatterns = [
    path("", ChatConfigView.as_view(), name="chatbot_named_config"),
    path("config/", ChatConfigView.as_view(), name="chatbot_named_config"),
    path("chat/", DefaultChatbotApiView.as_view(), name="chatbot_named_chat"),
    #
    # superfluous stuff that breaks the site unless it's included ...
    # -----------
    path("admin/", admin.site.urls),
    path("", include("smarter.urls.console")),
]

__all__ = ["urlpatterns"]
