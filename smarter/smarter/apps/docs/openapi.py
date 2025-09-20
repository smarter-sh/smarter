"""Configuration for OpenAPI documentation generation for Swagger and Redoc."""

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from smarter.apps.api import urls as api_urls


api_info = openapi.Info(
    title=settings.SMARTER_API_NAME,
    default_version="v1",
    description=settings.SMARTER_API_DESCRIPTION,
    terms_of_service="https:/smarter.sh/tos/",
    contact=openapi.Contact(
        name="Smarter Support",
        email="lpm0073@gmail.com",
        url="https://smarter.sh/contact/",
    ),
    license=openapi.License(
        name="AGPL-3.0 License",
        url="https://www.gnu.org/licenses/agpl-3.0.html",
    ),
)

schema_view = get_schema_view(
    info=api_info,
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=api_urls.urlpatterns,
)
