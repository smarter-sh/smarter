"""Django URL patterns for the Chat"""

from django.urls import include, path


urlpatterns = [
    path("", include("smarter.apps.plugin.api.v1.urls")),
    path("v1", include("smarter.apps.plugin.api.v1.urls")),
]
