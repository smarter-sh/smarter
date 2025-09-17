# pylint: disable=W0613
"""
Django REST framework base views for /docs/ brokered viewsets,
manifest and schema.
"""
import json
import os
from logging import getLogger
from typing import Optional
from urllib.parse import urlparse

import markdown
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.test import RequestFactory
from django.urls import reverse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_IS_INTERNAL_API_REQUEST, SmarterEnvironments
from smarter.common.exceptions import SmarterException
from smarter.lib.django.view_helpers import SmarterWebHtmlView
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys


logger = getLogger(__name__)

# note: this is the path from the Docker container, not the GitHub repo.
DOCS_PATH = "/home/smarter_user/data/docs/"


class DocsError(SmarterException):
    """Base class for all /docs/ errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter api docs error"


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsBaseView(SmarterWebHtmlView):
    """JSON Schema base view"""

    template_path: Optional[str] = None
    kind: Optional[SAMKinds] = None
    context: dict = {}

    def get_brokered_json_response(self, reverse_name: str, view, request: HttpRequest, *args, **kwargs):
        """Get the JSON response from the brokered smarter.sh/api endpoint."""
        if request.user is None:
            raise DocsError("request.user is None. This should not happen.")

        logger.info(
            "Getting brokered JSON response for reverse_name=%s, kind=%s, request.user=%s",
            reverse_name,
            self.kind,
            request.user.username if request.user.is_authenticated else "Anonymous",  # type: ignore[union-attr]
        )
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
        if hasattr(request, SMARTER_IS_INTERNAL_API_REQUEST):
            setattr(cli_request, SMARTER_IS_INTERNAL_API_REQUEST, getattr(request, SMARTER_IS_INTERNAL_API_REQUEST))
        else:
            setattr(cli_request, SMARTER_IS_INTERNAL_API_REQUEST, False)

        logger.info(
            "Creating brokered request for reverse_name=%s, kind=%s, request.user=%s",
            reverse_name,
            self.kind,
            cli_request.user.username if cli_request.user.is_authenticated else "Anonymous",  # type: ignore[union-attr]
        )
        response = view(request=cli_request, kind=self.kind.value, *args, **kwargs)
        json_response = json.loads(response.content.decode("utf-8"))

        if SmarterJournalApiResponseKeys.DATA in json_response:
            # unpack the smarter.sh/api response payload
            json_response = json_response[SmarterJournalApiResponseKeys.DATA]
        elif SmarterJournalApiResponseKeys.ERROR in json_response:
            # unpack the smarter.sh/api error response payload
            json_response = json_response[SmarterJournalApiResponseKeys.ERROR]

        logger.info(
            "Brokered JSON response for reverse_name=%s, kind=%s, request.user=%s: %s",
            reverse_name,
            self.kind,
            request.user.username if request.user.is_authenticated else "Anonymous",  # type: ignore[union-attr]
            json_response,
        )
        return json_response

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.context = {
            "og_url": self.smarter_build_absolute_uri(request),
            "canonical": request.path,
        }

        return super().dispatch(request, *args, **kwargs)  # type: ignore[return]


# ------------------------------------------------------------------------------
# Public Access Base Views
# ------------------------------------------------------------------------------
class TxtBaseView(SmarterWebHtmlView):
    """Text base view"""

    template_path = "docs/txt_file.html"
    text_file: Optional[str] = None
    title: Optional[str] = None
    leader: Optional[str] = None

    def get(self, request, *args, **kwargs):
        file_path = self.text_file
        if not file_path:
            raise DocsError("self.text_file not set.")

        with open(file_path, encoding="utf-8") as text_file:
            text_content = text_file.read()

        context = {
            "filecontents_html": text_content,
            "title": self.title,
            "leader": self.leader,
        }
        return render(request, self.template_path, context=context)


class MarkdownBaseView(SmarterWebHtmlView):
    """Markdown base view"""

    template_path = "docs/markdown.html"
    markdown_file: Optional[str] = None

    def get(self, request, *args, **kwargs):
        if not self.markdown_file:
            raise DocsError("self.markdown_file not set.")
        file_path = os.path.join(DOCS_PATH, self.markdown_file)
        with open(file_path, encoding="utf-8") as markdown_file:
            md_text = markdown_file.read()

        html = markdown.markdown(md_text)
        context = {
            "markdown_html": html,
        }

        return render(request, self.template_path, context=context)
