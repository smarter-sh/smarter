"""
URLs for the passthrough API views in the dashboard app.
"""

from django.urls import path

from smarter.common.utils.utils import camel_case_object_name

from .const import namespace
from .providers import ProviderApiView

app_name = namespace


class PassthroughApiReverseNames:
    """
    A class to hold the namespace for the passthrough API views in the dashboard app.
    """

    namespace = namespace

    api_providers = camel_case_object_name(ProviderApiView)


urlpatterns = [
    path("providers/", ProviderApiView.as_view(), name=PassthroughApiReverseNames.api_providers),
]
