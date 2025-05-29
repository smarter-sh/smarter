"""Django URL patterns for the Chat"""

from django.urls import include, path
from django.views.generic import RedirectView

from .const import namespace
from .v1.const import namespace as v1_namespace


app_name = namespace

urlpatterns = [
    path("", RedirectView.as_view(url="v1/")),
    path("v1", include("smarter.apps.chatbot.api.v1.urls", namespace=v1_namespace)),
]
