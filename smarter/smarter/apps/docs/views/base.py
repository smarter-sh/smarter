# pylint: disable=W0613
"""
Django REST framework base views for /docs/ brokered viewsets,
manifest and schema.
"""

import os
from logging import getLogger
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urlparse

import httpx
import markdown
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.test import RequestFactory
from django.urls import reverse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterException
from smarter.common.utils import is_authenticated_request
from smarter.lib import json
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
    SmarterWebHtmlView,
    SmarterWebTxtView,
)
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys

if TYPE_CHECKING:
    from django.http import HttpRequest
    from rest_framework.views import AsView

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
class DocsBaseView(SmarterAuthenticatedWebView):
    """JSON Schema base view"""

    template_path: Optional[str] = None
    name: Optional[str] = None
    kind: Optional[SAMKinds] = None
    context: dict = {}

    def get_brokered_json_response(
        self, reverse_name: str, view: "AsView", request: "HttpRequest", *args, **kwargs
    ) -> dict[str, Any]:
        """
        Get the JSON response from the brokered smarter.sh/api endpoint.
        This method constructs a brokered request to the specified API view, using
        Django's RequestFactory to create a new request object.
        The brokered request is made on behalf of the original request user to
        resolve possible permission issues related to object ownership in the
        API views, in cases where the authenticated user is not the owner of
        the object being accessed in the API view (e.g. a chatbot manifest).
        The response from the API view is expected to be a JSON response, which is then decoded
        and returned as a Python dictionary.

        Why we do this:
        Any authenticated user can access the /docs/ views, which contain links to all
        SAM resource kinds (e.g. chatbots, plugins, connections, etc.) regardless
        of ownership. Therefore, as a matter of standardized procedure, we spoof the
        resource owner when we make the brokered request to the API view
        to ensure that the user has sufficient access.


        Args:
            reverse_name (str): The name of the URL pattern to reverse for the API endpoint.
            view: The API view function or class-based view to call with the brokered request.
            request (HttpRequest): The original HTTP request object from the client.
            *args: Positional arguments to pass to the API view.
            **kwargs: Keyword arguments to pass to the API view.

        Returns:
            dict: The JSON response from the API view, decoded into a Python dictionary.
        """
        if not hasattr(request, "user") or request.user is None or not request.user.is_authenticated:
            logger.warning(
                "Request does not have a user associated with it. "
                "Anonymous requests may have limited access to certain manifests."
            )
            raise DocsError("Authentication required to access this resource.")

        if not self.template_path:
            raise DocsError("self.template_path not set.")
        if not self.kind:
            raise DocsError("self.kind not set.")

        logger.debug(
            "%s.get_brokered_json_response() reverse_name=%s, kind=%s, request.user=%s, args=%s, kwargs=%s",
            self.formatted_class_name,
            reverse_name,
            self.kind,
            request.user.username if is_authenticated_request(request) else "Anonymous",  # type: ignore[union-attr],
            args,
            kwargs,
        )

        scheme = "http" if smarter_settings.environment == SmarterEnvironments.LOCAL else "https"
        parsed_url = urlparse(smarter_settings.environment_url)

        factory = RequestFactory(SERVER_NAME=parsed_url.netloc, wsgi_url_scheme=scheme)
        path = str(reverse(reverse_name, kwargs={"kind": self.kind})).lower()
        logger.debug(
            "%s.get_brokered_json_response() resolved path for reverse_name=%s: %s",
            self.formatted_class_name,
            reverse_name,
            path,
        )
        cli_request = factory.post(path)
        cli_request.user = request.user

        # see comments below in dispatch() for why we set this flag,
        # but in short, this flag informs the DRF authentication
        # service that we're making a brokered request to our
        # own API views from inside an already-authenticated request,
        # and the brokered request is being made on behalf of the
        # original request user.
        cli_request = self.set_is_internal_api_request(cli_request, True)

        logger.debug(
            "%s.get_brokered_json_response() creating brokered request for path=%s, kind=%s, request.user=%s, args=%s, kwargs=%s",
            self.formatted_class_name,
            path,
            self.kind,
            cli_request.user.username if cli_request.user.is_authenticated else "Anonymous",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        response = view(request=cli_request, kind=self.kind.value, *args, **kwargs)
        if response.status_code != httpx.codes.OK:
            logger.error(
                "%s.get_brokered_json_response() received non-200 response for reverse_name=%s, kind=%s, request.user=%s response status: %s",
                self.formatted_class_name,
                reverse_name,
                self.kind,
                request.user.username if is_authenticated_request(request) else "Anonymous",  # type: ignore[union-attr]
                response.status_code if hasattr(response, "status_code") else "N/A",
            )
            raise DocsError(f"Received non-200 response from brokered view: {response.status_code}")

        try:
            json_response = json.loads(response.content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(
                "%s.get_brokered_json_response() failed to decode JSON response for reverse_name=%s, kind=%s, request.user=%s response status: %s, content: %s",
                self.formatted_class_name,
                reverse_name,
                self.kind,
                request.user.username if is_authenticated_request(request) else "Anonymous",  # type: ignore[union-attr]
                response.status_code if hasattr(response, "status_code") else "N/A",
                response.content if hasattr(response, "content") else "N/A",
            )
            raise DocsError("Failed to decode JSON response") from e

        if SmarterJournalApiResponseKeys.DATA in json_response:
            # unpack the smarter.sh/api response payload
            json_response = json_response[SmarterJournalApiResponseKeys.DATA]
        elif SmarterJournalApiResponseKeys.ERROR in json_response:
            # unpack the smarter.sh/api error response payload
            json_response = json_response[SmarterJournalApiResponseKeys.ERROR]

        logger.debug(
            "%s.get_brokered_json_response() brokered JSON response for reverse_name=%s, kind=%s, request.user=%s: %s",
            self.formatted_class_name,
            reverse_name,
            self.kind,
            request.user.username if is_authenticated_request(request) else "Anonymous",  # type: ignore[union-attr]
            json_response,
        )
        return json_response

    def dispatch(self, request: "HttpRequest", *args, **kwargs) -> HttpResponse:
        """
        Override dispatch to set up context and handle authentication for brokered
        API requests. Since the /docs/ views are publicly accessible to any
        authenticated user, and the brokered API requests made within these
        views need to be made on behalf of the original request user, we
        set a flag on the request to indicate that it's an internal API
        request. This allows us to use session authentication for the brokered
        requests without running into issues with missing or invalid tokens
        in DRF's token authentication.

        params:
        - request: The original HTTP request object from the client.
        - args: Positional arguments for the view.
        - kwargs: Keyword arguments for the view.

        returns:
        - HttpResponse: The HTTP response object returned by the view.
        """
        self.context = {}

        # This flag is used to circumvent DRF token authentication for the brokered
        # request we make to our own API views in get_brokered_json_response().
        # We want to use session authentication for the brokered request since
        # the user is already authenticated with a session cookie, and we
        # don't want DRF to reject the brokered request due to missing
        # or invalid token.
        #
        # This *probably* is not necessary since the brokered request is
        # made with RequestFactory, which will not include original
        # authentication credentials. However, we set this flag just
        # to be safe and to ensure that any downstream code that
        # checks for it will work correctly.
        request = self.set_is_internal_api_request(request, True)

        return super().dispatch(request, *args, **kwargs)  # type: ignore[return]

    def get(self, request, *args, **kwargs):
        return HttpResponseBadRequest("GET method not supported for this view.")

    def put(self, request, *args, **kwargs):
        return HttpResponseBadRequest("PUT method not supported for this view.")

    def patch(self, request, *args, **kwargs):
        return HttpResponseBadRequest("PATCH method not supported for this view.")

    def post(self, request, *args, **kwargs):
        raise NotImplementedError(
            "POST method not implemented for base view. This should be implemented in the subclass."
        )

    def delete(self, request, *args, **kwargs):
        return HttpResponseBadRequest("DELETE method not supported for this view.")


# ------------------------------------------------------------------------------
# Public Access Base Views
# ------------------------------------------------------------------------------
class TxtBaseView(SmarterWebTxtView):
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
