# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.

"""
import json
from urllib.parse import urlparse

from django.shortcuts import render
from django.test import RequestFactory
from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.schema import ApiV1CliSchemaApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.django.view_helpers import SmarterWebView
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsJsonSchemaBaseView(SmarterWebView):
    """JSON Schema base view"""

    template_path = "api/docs/json-schema.html"
    schema_kind: SAMKinds = None

    def get(self, request, *args, **kwargs):
        scheme = "http" if smarter_settings.environment == SmarterEnvironments.LOCAL else "https"
        parsed_url = urlparse(smarter_settings.environment_url)

        factory = RequestFactory(SERVER_NAME=parsed_url.netloc, wsgi_url_scheme=scheme)
        path = reverse(ApiV1CliReverseViews.schema, kwargs={"kind": self.schema_kind})
        cli_request = factory.get(path)
        cli_request.user = request.user

        view = ApiV1CliSchemaApiView.as_view()
        response = view(request=cli_request, kind=self.schema_kind.value, *args, **kwargs)
        json_response = json.loads(response.content.decode("utf-8"))

        if SmarterJournalApiResponseKeys.DATA in json_response:
            # unpack the smarter.sh/api response payload
            json_schema = json.dumps(json_response[SmarterJournalApiResponseKeys.DATA], indent=4)
        else:
            json_schema = json.dumps(json_response, indent=4)

        return render(request, self.template_path, {"json_schema": json_schema})


class DocsJsonSchemaAccountView(DocsJsonSchemaBaseView):
    """Account JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.ACCOUNT)


class DocsJsonSchemaApiConnectionView(DocsJsonSchemaBaseView):
    """ApiConnection JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.APICONNECTION)


class DocsJsonSchemaApiKeyView(DocsJsonSchemaBaseView):
    """ApiKey JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.APIKEY)


class DocsJsonSchemaChatView(DocsJsonSchemaBaseView):
    """Chat JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.CHAT)


class DocsJsonSchemaChatHistoryView(DocsJsonSchemaBaseView):
    """ChatHistory JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.CHAT_HISTORY)


class DocsJsonSchemaChatPluginUsageView(DocsJsonSchemaBaseView):
    """ChatPluginUsage JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.CHAT_PLUGIN_USAGE)


class DocsJsonSchemaChatToolCallView(DocsJsonSchemaBaseView):
    """ChatToolCall JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.CHAT_TOOL_CALL)


class DocsJsonSchemaChatBotView(DocsJsonSchemaBaseView):
    """ChatBot JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.CHATBOT)


class DocsJsonSchemaPluginView(DocsJsonSchemaBaseView):
    """Plugin JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.PLUGIN)


class DocsJsonSchemaSqlConnectionView(DocsJsonSchemaBaseView):
    """SqlConnection JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.SQLCONNECTION)


class DocsJsonSchemaUserView(DocsJsonSchemaBaseView):
    """User JSON Schema view"""

    schema_kind = SAMKinds(SAMKinds.USER)
