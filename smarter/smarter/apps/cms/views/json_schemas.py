# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
import json

from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.schema import ApiV1CliSchemaApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds

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
        json_response = self.get_brokered_json_response(ApiV1CliReverseViews.schema, view, request, *args, **kwargs)
        json_response = json.dumps(json_response, indent=4)

        return render(request, self.template_path, {"json_schema": json_response})


class DocsJsonSchemaAccountView(DocsJsonSchemaBaseView):
    """Account JSON Schema view"""

    kind = SAMKinds(SAMKinds.ACCOUNT)


class DocsJsonSchemaApiConnectionView(DocsJsonSchemaBaseView):
    """ApiConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.APICONNECTION)


class DocsJsonSchemaApiKeyView(DocsJsonSchemaBaseView):
    """ApiKey JSON Schema view"""

    kind = SAMKinds(SAMKinds.APIKEY)


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

    kind = SAMKinds(SAMKinds.PLUGIN)


class DocsJsonSchemaSqlConnectionView(DocsJsonSchemaBaseView):
    """SqlConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.SQLCONNECTION)


class DocsJsonSchemaUserView(DocsJsonSchemaBaseView):
    """User JSON Schema view"""

    kind = SAMKinds(SAMKinds.USER)
