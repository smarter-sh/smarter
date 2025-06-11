# pylint: disable=R0801,W0613
"""Customer API views."""

from http import HTTPStatus

from rest_framework.response import Response

from smarter.apps.provider.serializers import (
    ProviderModelSerializer,
    ProviderSerializer,
)
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)


class ProvidersApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for Providers list"""

    def get(self, request, *args, **kwargs):
        """Get all providers."""
        serializer = ProviderSerializer(many=True, context={"request": request})
        if not serializer.data:
            return SmarterHttpResponseNotFound("No providers found.")
        return Response(data=serializer.data, status=HTTPStatus.OK)


class ProviderApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for a specific provider"""

    def get(self, request, *args, name: str, **kwargs):
        """Get a specific provider by name."""
        serializer = ProviderSerializer(many=True, context={"request": request})
        if not serializer.data or len(serializer.data) == 0:
            return SmarterHttpResponseNotFound(f"Provider with name '{name}' not found.")
        if len(serializer.data) > 1:
            # If multiple providers are found, return a 500 error
            return SmarterHttpResponseServerError(
                "Multiple providers found with the same name. Please check your request."
            )
        return Response(data=serializer.data[0], status=HTTPStatus.OK)


class ProviderModelsApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for all models for a specific provider"""

    def get(self, request, *args, name: str, **kwargs):
        """Get all models for a specific provider."""
        serializer = ProviderModelSerializer(many=True, context={"request": request})
        if not serializer.data:
            return SmarterHttpResponseNotFound(f"No models found for provider '{name}'.")
        return Response(data=serializer.data, status=HTTPStatus.OK)


class ProviderModelApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for a specific model for a specific provider"""

    def get(self, request, *args, name: str, model_name: str, **kwargs):
        """Get a specific model for a specific provider."""
        serializer = ProviderModelSerializer(many=True, context={"request": request})
        if not serializer.data or len(serializer.data) == 0:
            return SmarterHttpResponseNotFound(f"Model '{model_name}' for provider '{name}' not found.")
        if len(serializer.data) > 1:
            # If multiple models are found, return a 500 error
            return SmarterHttpResponseServerError(
                "Multiple models found with the same name for the provider. Please check your request."
            )
        return Response(data=serializer.data[0], status=HTTPStatus.OK)
