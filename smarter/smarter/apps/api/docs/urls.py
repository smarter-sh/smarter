"""URL configuration for dashboard legal pages."""

from django.conf import settings
from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from .views.developer import (
    DeveloperDocsArchitectureView,
    DeveloperDocsChatBotApiView,
    DeveloperDocsCliView,
    DeveloperDocsDjangoReactView,
    DeveloperDocsGoodCodoingPracticeView,
    DeveloperDocsOpenAIGettingStartedView,
    DeveloperDocsSemanticVersioningView,
    DeveloperDocsTwelveFactorView,
)
from .views.json_schemas import (
    DocsJsonSchemaAccountView,
    DocsJsonSchemaApiConnectionView,
    DocsJsonSchemaApiKeyView,
    DocsJsonSchemaChatBotView,
    DocsJsonSchemaChatHistoryView,
    DocsJsonSchemaChatPluginUsageView,
    DocsJsonSchemaChatToolCallView,
    DocsJsonSchemaChatView,
    DocsJsonSchemaPluginView,
    DocsJsonSchemaSqlConnectionView,
    DocsJsonSchemaUserView,
)
from .views.manifests import (
    DocsExampleManifestAccountView,
    DocsExampleManifestApiConnectionView,
    DocsExampleManifestApiKeyView,
    DocsExampleManifestChatBotView,
    DocsExampleManifestChatHistoryView,
    DocsExampleManifestChatPluginUsageView,
    DocsExampleManifestChatToolCallView,
    DocsExampleManifestChatView,
    DocsExampleManifestPluginView,
    DocsExampleManifestSqlConnectionView,
    DocsExampleManifestUserView,
)
from .views.views import DocsView, SiteMapView


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
    path("", DocsView.as_view(), name="docs-home"),
    path("sitemap", SiteMapView.as_view(), name="sitemap"),
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    re_path(r"^swagger/$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc-ui"),
    path("json-schema/account/", DocsJsonSchemaAccountView.as_view(), name="json-schema-account"),
    path("json-schema/api-connection/", DocsJsonSchemaApiConnectionView.as_view(), name="json-schema-api-connection"),
    path("json-schema/api-key/", DocsJsonSchemaApiKeyView.as_view(), name="json-schema-api-key"),
    path("json-schema/chat/", DocsJsonSchemaChatView.as_view(), name="json-schema-chat"),
    path("json-schema/chat-history/", DocsJsonSchemaChatHistoryView.as_view(), name="json-schema-chat-history"),
    path(
        "json-schema/chat-plugin-usage/",
        DocsJsonSchemaChatPluginUsageView.as_view(),
        name="json-schema-chat-plugin-usage",
    ),
    path("json-schema/chat-tool-call/", DocsJsonSchemaChatToolCallView.as_view(), name="json-schema-chat-tool-call"),
    path("json-schema/chat-bot/", DocsJsonSchemaChatBotView.as_view(), name="json-schema-chat-bot"),
    path("json-schema/plugin/", DocsJsonSchemaPluginView.as_view(), name="json-schema-plugin"),
    path("json-schema/sql-connection/", DocsJsonSchemaSqlConnectionView.as_view(), name="json-schema-sql-connection"),
    path("json-schema/user/", DocsJsonSchemaUserView.as_view(), name="json-schema-user"),
    path("manifest/account/", DocsExampleManifestAccountView.as_view(), name="manifest-account"),
    path("manifest/api-connection/", DocsExampleManifestApiConnectionView.as_view(), name="manifest-api-connection"),
    path("manifest/api-key/", DocsExampleManifestApiKeyView.as_view(), name="manifest-api-key"),
    path("manifest/chat/", DocsExampleManifestChatView.as_view(), name="manifest-chat"),
    path("manifest/chat-history/", DocsExampleManifestChatHistoryView.as_view(), name="manifest-chat-history"),
    path(
        "manifest/chat-plugin-usage/",
        DocsExampleManifestChatPluginUsageView.as_view(),
        name="manifest-chat-plugin-usage",
    ),
    path("manifest/chat-tool-call/", DocsExampleManifestChatToolCallView.as_view(), name="manifest-chat-tool-call"),
    path("manifest/chat-bot/", DocsExampleManifestChatBotView.as_view(), name="manifest-chat-bot"),
    path("manifest/plugin/", DocsExampleManifestPluginView.as_view(), name="manifest-plugin"),
    path("manifest/sql-connection/", DocsExampleManifestSqlConnectionView.as_view(), name="manifest-sql-connection"),
    path("manifest/user/", DocsExampleManifestUserView.as_view(), name="manifest-user"),
    path("developer/12-factor/", DeveloperDocsTwelveFactorView.as_view(), name="developer-12-factor"),
    path("developer/architecture/", DeveloperDocsArchitectureView.as_view(), name="developer-architecture"),
    path("developer/chatbot-api/", DeveloperDocsChatBotApiView.as_view(), name="developer-chatbot-api"),
    path("developer/cli/", DeveloperDocsCliView.as_view(), name="developer-cli"),
    path("developer/django-react/", DeveloperDocsDjangoReactView.as_view(), name="developer-django-react"),
    path(
        "developer/good-coding-practice/",
        DeveloperDocsGoodCodoingPracticeView.as_view(),
        name="developer-good-coding-practice",
    ),
    path(
        "developer/openai-getting-started/",
        DeveloperDocsOpenAIGettingStartedView.as_view(),
        name="developer-openai-getting-started",
    ),
    path(
        "developer/semantic-versioning/",
        DeveloperDocsSemanticVersioningView.as_view(),
        name="developer-semantic-versioning",
    ),
]
