"""URL configuration for chat app."""

from django.urls import path

from .const import namespace
from .views.provider import (
    ProviderApiViewSet,
    ProviderModelApiViewSet,
    ProviderModelsApiViewSet,
    ProvidersApiViewSet,
)


app_name = namespace

urlpatterns = [
    path("", ProvidersApiViewSet.as_view(), name="providers_list"),
    path("<str:name>/", ProviderApiViewSet.as_view(), name="provider_detail"),
    path("<str:name>/models/", ProviderModelsApiViewSet.as_view(), name="provider_models_list"),
    path(
        "<str:name>/models/<str:model_name>",
        ProviderModelApiViewSet.as_view(),
        name="provider_model_detail",
    ),
]
