"""URL configuration for dashboard legal pages."""

from django.conf import settings
from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from smarter.apps.api.v1.manifests.enum import SAMKinds

from .utils import json_schema_name, json_schema_path, manifest_name, manifest_path
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
from .views.json_schema import (
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
from .views.manifest import (
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
from .views.views import JsonSchemasView, ManifestsView


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
    # -------------------------------------------------------------------------
    # Developers docs rendered from markdown in /data/doc/ in the Dockeer container
    # -------------------------------------------------------------------------
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
    # -------------------------------------------------------------------------
    # Documentation generators
    # -------------------------------------------------------------------------
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    re_path(r"^swagger/$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc-ui"),
    # -------------------------------------------------------------------------
    # JSON Schemas
    # -------------------------------------------------------------------------
    path(
        json_schema_path(SAMKinds.ACCOUNT), DocsJsonSchemaAccountView.as_view(), name=json_schema_name(SAMKinds.ACCOUNT)
    ),
    path(
        json_schema_path(SAMKinds.APICONNECTION),
        DocsJsonSchemaApiConnectionView.as_view(),
        name=json_schema_name(SAMKinds.APICONNECTION),
    ),
    path(json_schema_path(SAMKinds.APIKEY), DocsJsonSchemaApiKeyView.as_view(), name=json_schema_name(SAMKinds.APIKEY)),
    path(json_schema_path(SAMKinds.CHAT), DocsJsonSchemaChatView.as_view(), name=json_schema_name(SAMKinds.CHAT)),
    path(
        json_schema_path(SAMKinds.CHAT_HISTORY),
        DocsJsonSchemaChatHistoryView.as_view(),
        name=json_schema_name(SAMKinds.CHAT_HISTORY),
    ),
    path(
        json_schema_path(SAMKinds.CHAT_PLUGIN_USAGE),
        DocsJsonSchemaChatPluginUsageView.as_view(),
        name=json_schema_name(SAMKinds.CHAT_PLUGIN_USAGE),
    ),
    path(
        json_schema_path(SAMKinds.CHAT_TOOL_CALL),
        DocsJsonSchemaChatToolCallView.as_view(),
        name=json_schema_name(SAMKinds.CHAT_TOOL_CALL),
    ),
    path(
        json_schema_path(SAMKinds.CHATBOT), DocsJsonSchemaChatBotView.as_view(), name=json_schema_name(SAMKinds.CHATBOT)
    ),
    path(json_schema_path(SAMKinds.PLUGIN), DocsJsonSchemaPluginView.as_view(), name=json_schema_name(SAMKinds.PLUGIN)),
    path(
        json_schema_path(SAMKinds.SQLCONNECTION),
        DocsJsonSchemaSqlConnectionView.as_view(),
        name=json_schema_name(SAMKinds.SQLCONNECTION),
    ),
    path(json_schema_path(SAMKinds.USER), DocsJsonSchemaUserView.as_view(), name=json_schema_name(SAMKinds.USER)),
    # -------------------------------------------------------------------------
    # example manifests
    # -------------------------------------------------------------------------
    path(
        manifest_path(SAMKinds.ACCOUNT), DocsExampleManifestAccountView.as_view(), name=manifest_name(SAMKinds.ACCOUNT)
    ),
    path(
        manifest_path(SAMKinds.APICONNECTION),
        DocsExampleManifestApiConnectionView.as_view(),
        name=manifest_name(SAMKinds.APICONNECTION),
    ),
    path(manifest_path(SAMKinds.APIKEY), DocsExampleManifestApiKeyView.as_view(), name=manifest_name(SAMKinds.APIKEY)),
    path(manifest_path(SAMKinds.CHAT), DocsExampleManifestChatView.as_view(), name=manifest_name(SAMKinds.CHAT)),
    path(
        manifest_path(SAMKinds.CHAT_HISTORY),
        DocsExampleManifestChatHistoryView.as_view(),
        name=manifest_name(SAMKinds.CHAT_HISTORY),
    ),
    path(
        manifest_path(SAMKinds.CHAT_PLUGIN_USAGE),
        DocsExampleManifestChatPluginUsageView.as_view(),
        name=manifest_name(SAMKinds.CHAT_PLUGIN_USAGE),
    ),
    path(
        manifest_path(SAMKinds.CHAT_TOOL_CALL),
        DocsExampleManifestChatToolCallView.as_view(),
        name=manifest_name(SAMKinds.CHAT_TOOL_CALL),
    ),
    path(
        manifest_path(SAMKinds.CHATBOT), DocsExampleManifestChatBotView.as_view(), name=manifest_name(SAMKinds.CHATBOT)
    ),
    path(manifest_path(SAMKinds.PLUGIN), DocsExampleManifestPluginView.as_view(), name=manifest_name(SAMKinds.PLUGIN)),
    path(
        manifest_path(SAMKinds.SQLCONNECTION),
        DocsExampleManifestSqlConnectionView.as_view(),
        name=manifest_name(SAMKinds.SQLCONNECTION),
    ),
    path(manifest_path(SAMKinds.USER), DocsExampleManifestUserView.as_view(), name=manifest_name(SAMKinds.USER)),
    # -------------------------------------------------------------------------
    # manifests landing page
    # -------------------------------------------------------------------------
    path("manifests/", ManifestsView.as_view(), name="docs_manifests"),
    # -------------------------------------------------------------------------
    # json schemas landing page
    # -------------------------------------------------------------------------
    path("json-schemas/", JsonSchemasView.as_view(), name="docs_json_schemas"),
]
