# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.

"""
import json
from urllib.parse import urlparse

import yaml
from django.shortcuts import render
from django.test import RequestFactory
from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.manifest import ApiV1CliManifestApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.django.view_helpers import SmarterWebView
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsExampleManifestBaseView(SmarterWebView):
    """JSON Schema base view"""

    template_path = "api/docs/manifest.html"
    manifest_kind: SAMKinds = None

    def get(self, request, *args, **kwargs):
        scheme = "http" if smarter_settings.environment == SmarterEnvironments.LOCAL else "https"
        parsed_url = urlparse(smarter_settings.environment_url)

        factory = RequestFactory(SERVER_NAME=parsed_url.netloc, wsgi_url_scheme=scheme)
        path = reverse(ApiV1CliReverseViews.manifest, kwargs={"kind": self.manifest_kind})
        cli_request = factory.get(path)
        cli_request.user = request.user

        view = ApiV1CliManifestApiView.as_view()
        response = view(request=cli_request, kind=self.manifest_kind.value, *args, **kwargs)
        json_response = json.loads(response.content.decode("utf-8"))
        if SmarterJournalApiResponseKeys.DATA in json_response:
            # unpack the smarter.sh/api response payload
            json_response = json_response[SmarterJournalApiResponseKeys.DATA]
        elif SmarterJournalApiResponseKeys.ERROR in json_response:
            # unpack the smarter.sh/api error response payload
            json_response = json_response[SmarterJournalApiResponseKeys.ERROR]

        yaml_response = yaml.dump(json_response, default_flow_style=False)
        return render(request, self.template_path, {"manifest": yaml_response})


class DocsExampleManifestAccountView(DocsExampleManifestBaseView):
    """Account JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.ACCOUNT)


class DocsExampleManifestApiConnectionView(DocsExampleManifestBaseView):
    """ApiConnection JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.APICONNECTION)


class DocsExampleManifestApiKeyView(DocsExampleManifestBaseView):
    """ApiKey JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.APIKEY)


class DocsExampleManifestChatView(DocsExampleManifestBaseView):
    """Chat JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.CHAT)


class DocsExampleManifestChatHistoryView(DocsExampleManifestBaseView):
    """ChatHistory JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.CHAT_HISTORY)


class DocsExampleManifestChatPluginUsageView(DocsExampleManifestBaseView):
    """ChatPluginUsage JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.CHAT_PLUGIN_USAGE)


class DocsExampleManifestChatToolCallView(DocsExampleManifestBaseView):
    """ChatToolCall JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.CHAT_TOOL_CALL)


class DocsExampleManifestChatBotView(DocsExampleManifestBaseView):
    """ChatBot JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.CHATBOT)


class DocsExampleManifestPluginView(DocsExampleManifestBaseView):
    """Plugin JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.PLUGIN)


class DocsExampleManifestSqlConnectionView(DocsExampleManifestBaseView):
    """SqlConnection JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.SQLCONNECTION)


class DocsExampleManifestUserView(DocsExampleManifestBaseView):
    """User JSON Schema view"""

    manifest_kind = SAMKinds(SAMKinds.USER)
