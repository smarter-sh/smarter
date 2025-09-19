"""URL configuration for dashboard legal pages."""

from django.urls import path, re_path

from smarter.apps.api.v1.manifests.enum import SAMKinds

from .const import namespace
from .openapi import schema_view
from .utils import json_schema_name, json_schema_path, manifest_name, manifest_path
from .views.developer import (
    DeveloperDocsArchitectureView,
    DeveloperDocsChangelog,
    DeveloperDocsChatBotApiView,
    DeveloperDocsCliView,
    DeveloperDocsCodeOfConduct,
    DeveloperDocsDjangoReactView,
    DeveloperDocsDockerComposeView,
    DeveloperDocsDockerfileView,
    DeveloperDocsGoodCodoingPracticeView,
    DeveloperDocsMakefileView,
    DeveloperDocsOpenAIGettingStartedView,
    DeveloperDocsReadme,
    DeveloperDocsRequirementsView,
    DeveloperDocsSemanticVersioningView,
    DeveloperDocsTwelveFactorView,
    DeveloperDocsWeatherFunctionView,
)
from .views.json_schema import (
    DocsJsonSchemaAccountView,
    DocsJsonSchemaApiConnectionView,
    DocsJsonSchemaApiKeyView,
    DocsJsonSchemaApiView,
    DocsJsonSchemaChatBotView,
    DocsJsonSchemaChatHistoryView,
    DocsJsonSchemaChatPluginUsageView,
    DocsJsonSchemaChatToolCallView,
    DocsJsonSchemaChatView,
    DocsJsonSchemaPluginView,
    DocsJsonSchemaSecretView,
    DocsJsonSchemaSqlConnectionView,
    DocsJsonSchemaSqlView,
    DocsJsonSchemaUserView,
)
from .views.manifest import (
    DocsExampleManifestAccountView,
    DocsExampleManifestApiConnectionView,
    DocsExampleManifestApiKeyView,
    DocsExampleManifestApiView,
    DocsExampleManifestChatBotView,
    DocsExampleManifestChatHistoryView,
    DocsExampleManifestChatPluginUsageView,
    DocsExampleManifestChatToolCallView,
    DocsExampleManifestChatView,
    DocsExampleManifestPluginView,
    DocsExampleManifestSecretView,
    DocsExampleManifestSqlConnectionView,
    DocsExampleManifestSqlView,
    DocsExampleManifestUserView,
)
from .views.views import JsonSchemasView, ManifestsView


app_name = namespace
urlpatterns = [
    # -------------------------------------------------------------------------
    # Developers docs rendered from markdown in /data/docs/ in the Dockeer container
    # -------------------------------------------------------------------------
    path("developer/README.md/", DeveloperDocsReadme.as_view(), name="developer-readme"),
    path("developer/CHANGELOG.md/", DeveloperDocsChangelog.as_view(), name="developer-changelog"),
    path("developer/CODE_OF_CONDUCT.md/", DeveloperDocsCodeOfConduct.as_view(), name="developer-code-of-conduct"),
    path("developer/makefile/", DeveloperDocsMakefileView.as_view(), name="developer-makefile"),
    path("developer/weather-function/", DeveloperDocsWeatherFunctionView.as_view(), name="developer-weather-function"),
    path("developer/requirements/", DeveloperDocsRequirementsView.as_view(), name="developer-requirements"),
    path("developer/dockerfile/", DeveloperDocsDockerfileView.as_view(), name="developer-dockerfile"),
    path("developer/docker-compose/", DeveloperDocsDockerComposeView.as_view(), name="developer-docker-compose"),
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
        json_schema_path(SAMKinds.AUTH_TOKEN),
        DocsJsonSchemaApiKeyView.as_view(),
        name=json_schema_name(SAMKinds.AUTH_TOKEN),
    ),
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
    path(
        json_schema_path(SAMKinds.STATIC_PLUGIN),
        DocsJsonSchemaPluginView.as_view(),
        name=json_schema_name(SAMKinds.STATIC_PLUGIN),
    ),
    path(
        json_schema_path(SAMKinds.API_CONNECTION),
        DocsJsonSchemaApiConnectionView.as_view(),
        name=json_schema_name(SAMKinds.API_CONNECTION),
    ),
    path(
        json_schema_path(SAMKinds.API_PLUGIN),
        DocsJsonSchemaApiView.as_view(),
        name=json_schema_name(SAMKinds.API_PLUGIN),
    ),
    path(
        json_schema_path(SAMKinds.SQL_CONNECTION),
        DocsJsonSchemaSqlConnectionView.as_view(),
        name=json_schema_name(SAMKinds.SQL_CONNECTION),
    ),
    path(
        json_schema_path(SAMKinds.SQL_PLUGIN),
        DocsJsonSchemaSqlView.as_view(),
        name=json_schema_name(SAMKinds.SQL_PLUGIN),
    ),
    path(json_schema_path(SAMKinds.USER), DocsJsonSchemaUserView.as_view(), name=json_schema_name(SAMKinds.USER)),
    path(json_schema_path(SAMKinds.SECRET), DocsJsonSchemaSecretView.as_view(), name=json_schema_name(SAMKinds.SECRET)),
    # -------------------------------------------------------------------------
    # example manifests
    # -------------------------------------------------------------------------
    path(
        manifest_path(SAMKinds.ACCOUNT), DocsExampleManifestAccountView.as_view(), name=manifest_name(SAMKinds.ACCOUNT)
    ),
    path(
        manifest_path(SAMKinds.AUTH_TOKEN),
        DocsExampleManifestApiKeyView.as_view(),
        name=manifest_name(SAMKinds.AUTH_TOKEN),
    ),
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
    path(
        manifest_path(SAMKinds.STATIC_PLUGIN),
        DocsExampleManifestPluginView.as_view(),
        name=manifest_name(SAMKinds.STATIC_PLUGIN),
    ),
    path(
        manifest_path(SAMKinds.SQL_CONNECTION),
        DocsExampleManifestSqlConnectionView.as_view(),
        name=manifest_name(SAMKinds.SQL_CONNECTION),
    ),
    path(
        manifest_path(SAMKinds.SQL_PLUGIN),
        DocsExampleManifestSqlView.as_view(),
        name=manifest_name(SAMKinds.SQL_PLUGIN),
    ),
    path(
        manifest_path(SAMKinds.API_CONNECTION),
        DocsExampleManifestApiConnectionView.as_view(),
        name=manifest_name(SAMKinds.API_CONNECTION),
    ),
    path(
        manifest_path(SAMKinds.API_PLUGIN),
        DocsExampleManifestApiView.as_view(),
        name=manifest_name(SAMKinds.API_PLUGIN),
    ),
    path(manifest_path(SAMKinds.USER), DocsExampleManifestUserView.as_view(), name=manifest_name(SAMKinds.USER)),
    path(manifest_path(SAMKinds.SECRET), DocsExampleManifestSecretView.as_view(), name=manifest_name(SAMKinds.SECRET)),
    # -------------------------------------------------------------------------
    # manifests landing page
    # -------------------------------------------------------------------------
    path("manifests/", ManifestsView.as_view(), name="docs_manifests"),
    # -------------------------------------------------------------------------
    # json schemas landing page
    # -------------------------------------------------------------------------
    path("json-schemas/", JsonSchemasView.as_view(), name="docs_json_schemas"),
]
