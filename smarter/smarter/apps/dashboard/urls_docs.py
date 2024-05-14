"""URL configuration for dashboard legal pages."""

from django.conf import settings
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from .views.docs import GettingStartedView


schema_view = get_schema_view(
    openapi.Info(
        title=settings.SMARTER_API_NAME,
        default_version=settings.SMARTER_API_VERSION,
        description=settings.SMARTER_API_DESCRIPTION,
        terms_of_service="https:/smarter.sh/tos/",
        contact=openapi.Contact(email="contact@smarter.sh"),
        license=openapi.License(name="AGPL-3.0 License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path("getting-started/", GettingStartedView.as_view(), name="getting_started"),
    path("swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
