"""Django URL patterns for the Chat"""

from django.urls import include, path


urlpatterns = [
    path("api", include("smarter.apps.chatbot.api.urls")),
]
