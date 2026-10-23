# pylint: disable=W0613
"""Web server views for the docs app."""

import os
from datetime import datetime

from django.http import FileResponse, HttpResponse
from django.views import View

from smarter.apps.docs.urls import DocsReverseNames
from smarter.common.conf import smarter_settings
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterWebTxtView, SmarterWebXmlView


def absolute_url(path: str) -> str:
    """
    The absolute url of a path on this environment's platform host.

    :param path: An absolute path, e.g. ``/docs/manifests/``.
    :type path: str
    :returns: The url, e.g. ``https://platform.example.com/docs/manifests/``.
    :rtype: str
    """
    return f"{smarter_settings.environment_url.rstrip('/')}{path}"


def sitemap_pages() -> list[tuple[str, str]]:
    """
    The paths and priorities of the pages that sitemap.xml lists: the pages that anonymous visitors can read.

    Pages that require a login, redirects, machine-readable files such as openapi.json, and pages that
    robots.txt disallows, e.g. /login/, are left out.

    :returns: ``(path, priority)`` pairs, e.g. ``("/docs/manifests/", "0.8")``.
    :rtype: list[tuple[str, str]]
    """
    # smarter.urls.console imports this module.
    from smarter.urls.console import (  # pylint: disable=import-outside-toplevel
        ConsoleReverseNames,
    )

    docs = DocsReverseNames.namespace
    return [
        (reverse(docs, DocsReverseNames.example_manifests), "0.8"),
        (reverse(docs, DocsReverseNames.json_schemas), "0.8"),
        (reverse(docs, DocsReverseNames.openapi), "0.8"),
        (reverse(docs, DocsReverseNames.developer_readme), "0.6"),
        (reverse(docs, DocsReverseNames.developer_changelog), "0.6"),
        (reverse(docs, DocsReverseNames.developer_code_of_conduct), "0.6"),
        (reverse(docs, DocsReverseNames.developer_extension_protocol), "0.6"),
        (reverse(docs, DocsReverseNames.developer_makefile), "0.6"),
        (reverse(docs, DocsReverseNames.developer_requirements), "0.6"),
        (reverse(docs, DocsReverseNames.developer_dockerfile), "0.6"),
        (reverse(docs, DocsReverseNames.developer_docker_compose), "0.6"),
        (reverse(ConsoleReverseNames.register_view), "0.5"),
    ]


class RobotsTxtView(SmarterWebTxtView):
    """View to serve the robots.txt file."""

    template_path = "robots.txt"

    def get(self, request):
        """Render robots.txt with the sitemap's absolute url, which the robots exclusion standard requires."""
        # smarter.urls.console imports this module.
        from smarter.urls.console import (  # pylint: disable=import-outside-toplevel
            ConsoleReverseNames,
        )

        self.context = {"sitemap_url": absolute_url(reverse(ConsoleReverseNames.sitemap_xml))}
        return super().get(request)


class SitemapXmlView(SmarterWebXmlView):
    """View to serve the sitemap.xml file, which lists the platform's public pages (:func:`sitemap_pages`)."""

    template_path = "sitemap.xml"

    def get(self, request):
        """Render sitemap.xml with the absolute urls of :func:`sitemap_pages`."""
        self.context = {
            "urls": [{"loc": absolute_url(path), "priority": priority} for path, priority in sitemap_pages()],
            "lastmod": datetime.now().strftime("%Y-%m-01"),
            "changefreq": "monthly",
        }
        return super().get(request)


class FaviconView(View):
    """View to serve the favicon.ico file."""

    def get(self, request, *args, **kwargs):
        file_path = os.path.join("smarter", "static", "images", "logo", "favicon.ico")
        return FileResponse(open(file_path, "rb"), content_type="image/x-icon")


class HealthzView(View):
    """View to serve the healthz endpoint."""

    def get(self, request, *args, **kwargs):
        return HttpResponse("OK", content_type="text/plain")


class ReadinessView(View):
    """
    View to serve the readiness endpoint.

    Instantiate a LLMClientHelper object to
    force readiness of platform. This is the most likely collection of Python
    objects that will be used in the early stages of the application lifecycle.

    mcdaniel (aug-2025): squelching this idea for now as the overhead of instantiating
    LLMClientHelper is not worth the benefit at this stage.
    """

    def get(self, request, *args, **kwargs):
        # LLMClientHelper(request=request)
        return HttpResponse("OK", content_type="text/plain")
