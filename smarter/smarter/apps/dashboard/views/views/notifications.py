# pylint: disable=W0613
"""Django views"""

from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class NotificationsView(SmarterAuthenticatedWebView):
    """Notifications view"""

    template_path = "dashboard/notifications.html"
