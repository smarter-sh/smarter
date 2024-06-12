# pylint: disable=W0613
"""Django REST framework views for the API admin app."""

import yaml
from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.manifest import ApiV1CliManifestApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds

from .base import DocsBaseView


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsExampleManifestBaseView(DocsBaseView):
    """JSON Schema base view"""

    template_path = "api/docs/manifest.html"
    kind: SAMKinds = None

    def get(self, request, *args, **kwargs):
        view = ApiV1CliManifestApiView.as_view()
        json_response = self.get_brokered_json_response(ApiV1CliReverseViews.manifest, view, request, *args, **kwargs)

        yaml_response = yaml.dump(json_response, default_flow_style=False)
        return render(request, self.template_path, {"manifest": yaml_response})


class DocsExampleManifestAccountView(DocsExampleManifestBaseView):
    """Account JSON Schema view"""

    kind = SAMKinds(SAMKinds.ACCOUNT)


class DocsExampleManifestApiConnectionView(DocsExampleManifestBaseView):
    """ApiConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.APICONNECTION)


class DocsExampleManifestApiKeyView(DocsExampleManifestBaseView):
    """ApiKey JSON Schema view"""

    kind = SAMKinds(SAMKinds.APIKEY)


class DocsExampleManifestChatView(DocsExampleManifestBaseView):
    """Chat JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT)


class DocsExampleManifestChatHistoryView(DocsExampleManifestBaseView):
    """ChatHistory JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT_HISTORY)


class DocsExampleManifestChatPluginUsageView(DocsExampleManifestBaseView):
    """ChatPluginUsage JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT_PLUGIN_USAGE)


class DocsExampleManifestChatToolCallView(DocsExampleManifestBaseView):
    """ChatToolCall JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHAT_TOOL_CALL)


class DocsExampleManifestChatBotView(DocsExampleManifestBaseView):
    """ChatBot JSON Schema view"""

    kind = SAMKinds(SAMKinds.CHATBOT)


class DocsExampleManifestPluginView(DocsExampleManifestBaseView):
    """Plugin JSON Schema view"""

    kind = SAMKinds(SAMKinds.PLUGIN)


class DocsExampleManifestSqlConnectionView(DocsExampleManifestBaseView):
    """SqlConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.SQLCONNECTION)


class DocsExampleManifestUserView(DocsExampleManifestBaseView):
    """User JSON Schema view"""

    kind = SAMKinds(SAMKinds.USER)
