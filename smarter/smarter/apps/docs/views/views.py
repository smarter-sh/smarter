# pylint: disable=W0613
"""Django REST framework views for the API admin app."""

from smarter.lib.django.view_helpers import SmarterNeverCachedWebView, SmarterWebView


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsView(SmarterWebView):
    """/docs/ landing page view"""

    template_path = "docs/index.html"


class DocsApiView(SmarterWebView):
    """/docs/api/ landing page view"""

    template_path = "docs/api.html"


class DocsCliView(SmarterWebView):
    """/docs/cli/ landing page view"""

    template_path = "docs/cli.html"


class DocsDevelopersView(SmarterWebView):
    """/docs/developers/ landing page view"""

    template_path = "docs/developers.html"


class DocsLearnView(SmarterWebView):
    """/docs/api/ landing page view"""

    template_path = "docs/learn.html"


class DocsJsonSchemasView(SmarterWebView):
    """/docs/json-schemas/ landing page view"""

    template_path = "docs/json-schemas.html"


class DocsManifestsView(SmarterWebView):
    """/docs/manifests/ landing page view"""

    template_path = "docs/manifests.html"


class SiteMapView(SmarterNeverCachedWebView):
    """/docs/sitemap/ Keen sample page view"""

    template_path = "docs/sitemap.html"
