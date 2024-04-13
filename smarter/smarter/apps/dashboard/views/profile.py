# pylint: disable=C0115
"""Django views"""
import logging

from smarter.common.helpers.view_helpers import SmarterAuthenticatedWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class ProfileView(SmarterAuthenticatedWebView):

    template_path = "dashboard/profile/profile.html"


class ProfileLanguageView(SmarterAuthenticatedWebView):

    template_path = "dashboard/profile/language.html"
