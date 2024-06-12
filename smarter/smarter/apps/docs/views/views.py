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


class SiteMapView(SmarterNeverCachedWebView):
    """/docs/sitemap/ Keen sample page view"""

    template_path = "docs/sitemap.html"
