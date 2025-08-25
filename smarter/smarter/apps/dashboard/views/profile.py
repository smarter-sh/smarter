# pylint: disable=C0115
"""Django views"""

from smarter.lib.django.view_helpers import SmarterAuthenticatedWebView


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class ProfileView(SmarterAuthenticatedWebView):

    template_path = "dashboard/profile/profile.html"


class ProfileLanguageView(SmarterAuthenticatedWebView):

    template_path = "dashboard/profile/language.html"
