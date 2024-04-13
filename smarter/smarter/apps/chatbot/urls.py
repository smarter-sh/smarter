"""Django URL patterns for the chatapp"""

from django.urls import include, path

from smarter.apps.chatapp.views import ChatAppView


urlpatterns = [
    path("", include("smarter.apps.chatbot.api.v0.urls")),
    path("webapp", ChatAppView.as_view(), name="webapp"),
]
