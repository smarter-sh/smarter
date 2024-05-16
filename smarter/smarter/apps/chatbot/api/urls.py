"""Django URL patterns for the Chat"""

from django.urls import include, path


urlpatterns = [
    path("", include("smarter.apps.chatbot.api.v1.urls")),
    path("v0", include("smarter.apps.chatbot.api.v0.urls")),
    path("v1", include("smarter.apps.chatbot.api.v1.urls")),
]
