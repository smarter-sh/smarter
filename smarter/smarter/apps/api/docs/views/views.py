# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.

"""
from smarter.lib.django.view_helpers import SmarterNeverCachedWebView, SmarterWebView


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsView(SmarterWebView):
    """/api/docs/ landing page view"""

    template_path = "api/docs/index.html"


class SiteMapView(SmarterNeverCachedWebView):
    """/api/docs/sitemap/ Keen sample page view"""

    template_path = "api/docs/sitemap.html"
