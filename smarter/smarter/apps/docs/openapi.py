"""Configuration for OpenAPI documentation generation for Swagger and Redoc."""

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from smarter.apps.api import urls as api_urls
from smarter.common.conf import settings as smarter_settings


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


class ApiKeySchemaGenerator(OpenAPISchemaGenerator):
    """Custom schema generator to add API key auth while preserving default session auth."""

    def get_security_definitions(self):
        security_defs = super().get_security_definitions()
        if not isinstance(security_defs, dict):
            security_defs = {}
        security_defs["ApiKeyAuth"] = {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter your token as: Token <your_token>",
        }
        return security_defs


schema_view = get_schema_view(
    info=api_info,
    url=smarter_settings.environment_api_url,
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=api_urls.urlpatterns,
    generator_class=ApiKeySchemaGenerator,
)
