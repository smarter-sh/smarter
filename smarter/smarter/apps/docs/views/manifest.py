# pylint: disable=W0613
"""Django REST framework views for the API admin app."""

import yaml
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.manifest import ApiV1CliManifestApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.utils import pascal_to_snake

from .base import DocsBaseView


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsExampleManifestBaseView(DocsBaseView):
    """JSON Schema base view"""

    template_path = "docs/manifest.html"
    kind: SAMKinds
    file_name: str

    def get(self, request, *args, **kwargs):
        """
        For Waggtail docs generation, we want the HTML page with the YAML output embedded.
        """
        view = ApiV1CliManifestApiView.as_view()
        json_response = self.get_brokered_json_response(
            ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.manifest, view, request, *args, **kwargs
        )

        yaml_response = yaml.dump(json_response, default_flow_style=False)
        self.context["manifest"] = yaml_response
        if not isinstance(self.template_path, str):
            raise ValueError("Template path must be a string")
        return render(request, self.template_path, context=self.context)

    def post(self, request, *args, **kwargs):
        """
        For Sphinx docs generation, we just want the raw YAML output
        rather than the HTML page.
        """
        self.file_name = str(self.kind)
        self.file_name = str(pascal_to_snake(self.file_name)) + ".yaml"

        view = ApiV1CliManifestApiView.as_view()
        json_response = self.get_brokered_json_response(
            ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.manifest, view, request, *args, **kwargs
        )

        yaml_response = yaml.dump(json_response, default_flow_style=False)
        return HttpResponse(yaml_response, content_type="text/plain")


class DocsExampleManifestAccountView(DocsExampleManifestBaseView):
    """Account JSON Schema view"""

    kind = SAMKinds(SAMKinds.ACCOUNT)


class DocsExampleManifestApiConnectionView(DocsExampleManifestBaseView):
    """ApiConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.API_CONNECTION)


class DocsExampleManifestApiView(DocsExampleManifestBaseView):
    """Plugin Api JSON Schema view"""

    kind = SAMKinds(SAMKinds.API_PLUGIN)


class DocsExampleManifestApiKeyView(DocsExampleManifestBaseView):
    """ApiKey JSON Schema view"""

    kind = SAMKinds(SAMKinds.AUTH_TOKEN)


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

    kind = SAMKinds(SAMKinds.STATIC_PLUGIN)


class DocsExampleManifestSqlConnectionView(DocsExampleManifestBaseView):
    """SqlConnection JSON Schema view"""

    kind = SAMKinds(SAMKinds.SQL_CONNECTION)


class DocsExampleManifestSqlView(DocsExampleManifestBaseView):
    """Plugin Sql JSON Schema view"""

    kind = SAMKinds(SAMKinds.SQL_PLUGIN)


class DocsExampleManifestUserView(DocsExampleManifestBaseView):
    """User JSON Schema view"""

    kind = SAMKinds(SAMKinds.USER)


class DocsExampleManifestSecretView(DocsExampleManifestBaseView):
    """Secret JSON Schema view"""

    kind = SAMKinds(SAMKinds.SECRET)
