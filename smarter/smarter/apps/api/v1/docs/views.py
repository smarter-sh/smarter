# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
import logging

from smarter.lib.django.view_helpers import SmarterWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class GettingStartedView(SmarterWebView):
    """Top level legal view"""

    template_path = "api/v1/docs/getting-started.html"
