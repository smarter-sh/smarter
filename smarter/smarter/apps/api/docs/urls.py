"""URL configuration for dashboard legal pages."""

from django.conf import settings
from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from .views import Sitemap


schema_view = get_schema_view(
    openapi.Info(
        title=settings.SMARTER_API_NAME,
        default_version="v1",
        description=settings.SMARTER_API_DESCRIPTION,
        terms_of_service="https:/smarter.sh/tos/",
        contact=openapi.Contact(email="contact@smarter.sh"),
        license=openapi.License(name="AGPL-3.0 License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path("", Sitemap.as_view(), name="getting_started"),
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    re_path(r"^swagger/$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
