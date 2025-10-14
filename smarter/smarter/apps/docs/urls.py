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
        json_schema_path(SAMKinds.ACCOUNT.value),
        DocsJsonSchemaAccountView.as_view(),
        name=json_schema_name(SAMKinds.ACCOUNT.value),
    ),
    path(
        json_schema_path(SAMKinds.AUTH_TOKEN.value),
        DocsJsonSchemaApiKeyView.as_view(),
        name=json_schema_name(SAMKinds.AUTH_TOKEN.value),
    ),
    path(
        json_schema_path(SAMKinds.CHAT.value),
        DocsJsonSchemaChatView.as_view(),
        name=json_schema_name(SAMKinds.CHAT.value),
    ),
    path(
        json_schema_path(SAMKinds.CHAT_HISTORY.value),
        DocsJsonSchemaChatHistoryView.as_view(),
        name=json_schema_name(SAMKinds.CHAT_HISTORY.value),
    ),
    path(
        json_schema_path(SAMKinds.CHAT_PLUGIN_USAGE.value),
        DocsJsonSchemaChatPluginUsageView.as_view(),
        name=json_schema_name(SAMKinds.CHAT_PLUGIN_USAGE.value),
    ),
    path(
        json_schema_path(SAMKinds.CHAT_TOOL_CALL.value),
        DocsJsonSchemaChatToolCallView.as_view(),
        name=json_schema_name(SAMKinds.CHAT_TOOL_CALL.value),
    ),
    path(
        json_schema_path(SAMKinds.CHATBOT.value),
        DocsJsonSchemaChatBotView.as_view(),
        name=json_schema_name(SAMKinds.CHATBOT.value),
    ),
    path(
        json_schema_path(SAMKinds.STATIC_PLUGIN.value),
        DocsJsonSchemaPluginView.as_view(),
        name=json_schema_name(SAMKinds.STATIC_PLUGIN.value),
    ),
    path(
        json_schema_path(SAMKinds.API_CONNECTION.value),
        DocsJsonSchemaApiConnectionView.as_view(),
        name=json_schema_name(SAMKinds.API_CONNECTION.value),
    ),
    path(
        json_schema_path(SAMKinds.API_PLUGIN.value),
        DocsJsonSchemaApiView.as_view(),
        name=json_schema_name(SAMKinds.API_PLUGIN.value),
    ),
    path(
        json_schema_path(SAMKinds.SQL_CONNECTION.value),
        DocsJsonSchemaSqlConnectionView.as_view(),
        name=json_schema_name(SAMKinds.SQL_CONNECTION.value),
    ),
    path(
        json_schema_path(SAMKinds.SQL_PLUGIN.value),
        DocsJsonSchemaSqlView.as_view(),
        name=json_schema_name(SAMKinds.SQL_PLUGIN.value),
    ),
    path(
        json_schema_path(SAMKinds.USER.value),
        DocsJsonSchemaUserView.as_view(),
        name=json_schema_name(SAMKinds.USER.value),
    ),
    path(
        json_schema_path(SAMKinds.SECRET.value),
        DocsJsonSchemaSecretView.as_view(),
        name=json_schema_name(SAMKinds.SECRET.value),
    ),
    # -------------------------------------------------------------------------
    # example manifests
    # -------------------------------------------------------------------------
    path(
        manifest_path(SAMKinds.ACCOUNT.value),
        DocsExampleManifestAccountView.as_view(),
        name=manifest_name(SAMKinds.ACCOUNT.value),
    ),
    path(
        manifest_path(SAMKinds.AUTH_TOKEN.value),
        DocsExampleManifestApiKeyView.as_view(),
        name=manifest_name(SAMKinds.AUTH_TOKEN.value),
    ),
    path(
        manifest_path(SAMKinds.CHAT.value),
        DocsExampleManifestChatView.as_view(),
        name=manifest_name(SAMKinds.CHAT.value),
    ),
    path(
        manifest_path(SAMKinds.CHAT_HISTORY.value),
        DocsExampleManifestChatHistoryView.as_view(),
        name=manifest_name(SAMKinds.CHAT_HISTORY.value),
    ),
    path(
        manifest_path(SAMKinds.CHAT_PLUGIN_USAGE.value),
        DocsExampleManifestChatPluginUsageView.as_view(),
        name=manifest_name(SAMKinds.CHAT_PLUGIN_USAGE.value),
    ),
    path(
        manifest_path(SAMKinds.CHAT_TOOL_CALL.value),
        DocsExampleManifestChatToolCallView.as_view(),
        name=manifest_name(SAMKinds.CHAT_TOOL_CALL.value),
    ),
    path(
        manifest_path(SAMKinds.CHATBOT.value),
        DocsExampleManifestChatBotView.as_view(),
        name=manifest_name(SAMKinds.CHATBOT.value),
    ),
    path(
        manifest_path(SAMKinds.STATIC_PLUGIN.value),
        DocsExampleManifestPluginView.as_view(),
        name=manifest_name(SAMKinds.STATIC_PLUGIN.value),
    ),
    path(
        manifest_path(SAMKinds.SQL_CONNECTION.value),
        DocsExampleManifestSqlConnectionView.as_view(),
        name=manifest_name(SAMKinds.SQL_CONNECTION.value),
    ),
    path(
        manifest_path(SAMKinds.SQL_PLUGIN.value),
        DocsExampleManifestSqlView.as_view(),
        name=manifest_name(SAMKinds.SQL_PLUGIN.value),
    ),
    path(
        manifest_path(SAMKinds.API_CONNECTION.value),
        DocsExampleManifestApiConnectionView.as_view(),
        name=manifest_name(SAMKinds.API_CONNECTION.value),
    ),
    path(
        manifest_path(SAMKinds.API_PLUGIN.value),
        DocsExampleManifestApiView.as_view(),
        name=manifest_name(SAMKinds.API_PLUGIN.value),
    ),
    path(
        manifest_path(SAMKinds.USER.value),
        DocsExampleManifestUserView.as_view(),
        name=manifest_name(SAMKinds.USER.value),
    ),
    path(
        manifest_path(SAMKinds.SECRET.value),
        DocsExampleManifestSecretView.as_view(),
        name=manifest_name(SAMKinds.SECRET.value),
    ),
    # -------------------------------------------------------------------------
    # manifests landing page
    # -------------------------------------------------------------------------
    path("manifests/", ManifestsView.as_view(), name="docs_manifests"),
    # -------------------------------------------------------------------------
    # json schemas landing page
    # -------------------------------------------------------------------------
    path("json-schemas/", JsonSchemasView.as_view(), name="docs_json_schemas"),
]
