# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.

"""
import logging

from smarter.lib.django.view_helpers import SmarterNeverCachedWebView, SmarterWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocsView(SmarterWebView):
    """Top level legal view"""

    template_path = "api/docs/index.html"


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class SiteMapView(SmarterNeverCachedWebView):
    """Top level legal view"""

    template_path = "api/docs/sitemap.html"
