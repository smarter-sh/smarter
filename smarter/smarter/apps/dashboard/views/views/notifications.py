# pylint: disable=W0613
"""
Dashboard notifications view.

This module provides an authenticated view that renders the notifications page
for logged-in users.

Classes:
    NotificationsView: Authenticated view that renders the dashboard
        notifications page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.views.notifications import NotificationsView

        urlpatterns = [
            path("notifications/", NotificationsView.as_view(), name="notifications"),
        ]
"""

from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class NotificationsView(SmarterAuthenticatedWebView):
    """
    Authenticated view that renders the dashboard notifications page.

    Extends :class:`~smarter.lib.django.views.SmarterAuthenticatedWebView` to
    restrict access to authenticated users.

    Attributes:
        template_path (str): ``"dashboard/notifications.html"``
    """

    template_path = "dashboard/notifications.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{NotificationsView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)
