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
from smarter.common.exceptions import SmarterExceptionBase
from smarter.lib.django.view_helpers import SmarterWebView
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys


class DocsError(SmarterExceptionBase):
    """Base class for all /api/docs/ errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter api docs error"


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsBaseView(SmarterWebView):
    """JSON Schema base view"""

    template_path: str = None
    kind: SAMKinds = None

    def get_brokered_json_response(self, reverse_name: str, request, *args, **kwargs):
        """Get the JSON response from the brokered smarter.sh/api endpoint."""
        if not self.template_path:
            raise DocsError("self.template_path not set.")
        if not self.kind:
            raise DocsError("self.kind not set.")

        scheme = "http" if smarter_settings.environment == SmarterEnvironments.LOCAL else "https"
        parsed_url = urlparse(smarter_settings.environment_url)

        factory = RequestFactory(SERVER_NAME=parsed_url.netloc, wsgi_url_scheme=scheme)
        path = reverse(reverse_name, kwargs={"kind": self.kind})
        cli_request = factory.get(path)
        cli_request.user = request.user

        view = ApiV1CliManifestApiView.as_view()
        response = view(request=cli_request, kind=self.kind.value, *args, **kwargs)
        json_response = json.loads(response.content.decode("utf-8"))

        if SmarterJournalApiResponseKeys.DATA in json_response:
            # unpack the smarter.sh/api response payload
            json_response = json_response[SmarterJournalApiResponseKeys.DATA]
        elif SmarterJournalApiResponseKeys.ERROR in json_response:
            # unpack the smarter.sh/api error response payload
            json_response = json_response[SmarterJournalApiResponseKeys.ERROR]

        return json_response
