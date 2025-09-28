# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.schema import ApiV1CliSchemaApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib import json

from .base import DocsBaseView


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsJsonSchemaBaseView(DocsBaseView):
    """JSON Schema base view"""

    template_path = "docs/json-schema.html"
    kind: SAMKinds = None

    def get(self, request, *args, **kwargs):
        view = ApiV1CliSchemaApiView.as_view()
        json_response = self.get_brokered_json_response(
            ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.schema, view, request, *args, **kwargs
        )
        json_response = json.dumps(json_response)
        self.context["json_schema"] = json_response
        return render(request, self.template_path, context=self.context)


class DocsJsonSchemaAccountView(DocsJsonSchemaBaseView):
    """Account JSON Schema view"""

    kind = SAMKinds(SAMKinds.ACCOUNT)


class DocsJsonSchemaApiConnectionView(DocsJsonSchemaBaseView):
    """ApiConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.API_CONNECTION)


class DocsJsonSchemaApiView(DocsJsonSchemaBaseView):
    """Plugin Api JSON Schema view"""

    kind = SAMKinds(SAMKinds.API_PLUGIN)


class DocsJsonSchemaApiKeyView(DocsJsonSchemaBaseView):
    """ApiKey JSON Schema view"""

    kind = SAMKinds(SAMKinds.AUTH_TOKEN)


class DocsJsonSchemaChatView(DocsJsonSchemaBaseView):
    """Chat JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT)


class DocsJsonSchemaChatHistoryView(DocsJsonSchemaBaseView):
    """ChatHistory JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT_HISTORY)


class DocsJsonSchemaChatPluginUsageView(DocsJsonSchemaBaseView):
    """ChatPluginUsage JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT_PLUGIN_USAGE)


class DocsJsonSchemaChatToolCallView(DocsJsonSchemaBaseView):
    """ChatToolCall JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT_TOOL_CALL)


class DocsJsonSchemaChatBotView(DocsJsonSchemaBaseView):
    """ChatBot JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHATBOT)


class DocsJsonSchemaPluginView(DocsJsonSchemaBaseView):
    """Plugin JSON Schema view"""

    kind = SAMKinds(SAMKinds.STATIC_PLUGIN)


class DocsJsonSchemaSqlConnectionView(DocsJsonSchemaBaseView):
    """SqlConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.SQL_CONNECTION)


class DocsJsonSchemaSqlView(DocsJsonSchemaBaseView):
    """Plugin Sql JSON Schema view"""

    kind = SAMKinds(SAMKinds.SQL_PLUGIN)


class DocsJsonSchemaUserView(DocsJsonSchemaBaseView):
    """User JSON Schema view"""

    kind = SAMKinds(SAMKinds.SECRET)


class DocsJsonSchemaSecretView(DocsJsonSchemaBaseView):
    """Secret JSON Schema view"""

    kind = SAMKinds(SAMKinds.SECRET)
