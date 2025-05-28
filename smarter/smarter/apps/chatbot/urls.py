"""Django URL patterns for the Chat"""

from django.urls import include, path

from .const import namespace


app_name = namespace

urlpatterns = [
    path("api", include("smarter.apps.chatbot.api.urls", namespace="api")),
]
