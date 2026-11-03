# pylint: disable=C0115
"""Django views."""

from smarter.lib.django.views import SmarterAuthenticatedWebView


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class ProfileView(SmarterAuthenticatedWebView):
    """The web console's user profile page."""

    template_path = "dashboard/profile/profile.html"


class ProfileLanguageView(SmarterAuthenticatedWebView):
    """The web console's page for choosing the user's language."""

    template_path = "dashboard/profile/language.html"
