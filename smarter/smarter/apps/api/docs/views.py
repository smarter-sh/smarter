# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.

"""
import logging

from smarter.lib.django.view_helpers import SmarterWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DocumentationHomePage(SmarterWebView):
    """Top level legal view"""

    template_path = "api/docs/sitemap.html"
