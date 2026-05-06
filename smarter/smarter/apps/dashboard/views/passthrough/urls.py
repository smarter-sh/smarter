"""URL configuration for the Dashboard app's passthrough views."""

from django.urls import include, path

from smarter.common.utils import camel_case_object_name

from .api import urls as api_urls
from .const import namespace
from .view import PromptPassthroughView

app_name = namespace


class PassthroughReverseNames:
    """
    A class to hold the namespace for the passthrough views in the dashboard app.
    """

    namespace = namespace

    view = camel_case_object_name(PromptPassthroughView)


urlpatterns = [
    path("", PromptPassthroughView.as_view(), name=PassthroughReverseNames.view),
    path("api/", include(api_urls, api_urls.namespace)),
]
