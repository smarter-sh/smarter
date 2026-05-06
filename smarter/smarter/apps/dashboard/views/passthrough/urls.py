"""URL configuration for the Dashboard app's passthrough views."""

from django.urls import path

from smarter.apps.dashboard.const import namespace
from smarter.common.utils import camel_case_object_name

from . import PromptPassthroughView, ProviderApiView


class PassthroughReverseNames:
    """
    A class to hold the namespace for the passthrough views in the dashboard app.
    """

    namespace = namespace

    view = camel_case_object_name(PromptPassthroughView)
    api_providers = camel_case_object_name(ProviderApiView)


urlpatterns = [
    path("", PromptPassthroughView.as_view(), name=PassthroughReverseNames.view),
    path("api/providers/", ProviderApiView.as_view(), name=PassthroughReverseNames.api_providers),
]
