"""Django URL patterns for the chatapp"""

from django.urls import include, path

from smarter.apps.chatapp.views import ChatAppView

from .views.smarter import SmarterChatBotApiView


urlpatterns = [
    path("", SmarterChatBotApiView.as_view(), name="smarter-chat-api"),
    path("", include("smarter.apps.chatbot.api.v0.urls")),
    path("webapp", ChatAppView.as_view(), name="webapp"),
]
