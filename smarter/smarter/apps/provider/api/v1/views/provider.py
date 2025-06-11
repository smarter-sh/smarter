# pylint: disable=R0801,W0613
"""Customer API views."""

from rest_framework.response import Response

from smarter.apps.provider.models import (
    get_model_for_provider,
    get_models_for_provider,
    get_provider,
    get_providers,
)
from smarter.common.exceptions import SmarterException
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)


class ProvidersApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for openai api function calling"""

    def get(self, request, *args, **kwargs):
        """Get all providers."""
        try:
            providers = get_providers()
        except SmarterException:
            return SmarterHttpResponseNotFound(request=request, error_message="No providers found")

        return Response(providers)


class ProviderApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for openai api function calling"""

    def get(self, request, *args, name: str, **kwargs):
        """Get a specific provider by name."""
        try:
            provider = get_provider(provider_name=name)
        except SmarterException:
            return SmarterHttpResponseNotFound(request=request, error_message="Provider not found")

        return Response(provider)


class ProviderModelsApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for openai api function calling"""

    def get(self, request, *args, name: str, **kwargs):
        """Get all models for a specific provider."""
        try:
            models = get_models_for_provider(provider_name=name)
        except SmarterException:
            return SmarterHttpResponseNotFound(request=request, error_message="No models found for this provider")

        return Response(models)


class ProviderModelApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for openai api function calling"""

    def get(self, request, *args, name: str, model_name: str, **kwargs):
        """Get a specific model for a specific provider."""
        try:
            model = get_model_for_provider(provider_name=name, model_name=model_name)
        except SmarterException:
            return SmarterHttpResponseNotFound(request=request, error_message="Model not found for this provider")

        return Response(model)
