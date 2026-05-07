# pylint: disable=W0613
"""
Dashboard changelog view.

This module provides a publicly accessible view that renders the platform
changelog page. The page is served as a static HTML render of
``dashboard/changelog.html`` with no authentication requirement.

Classes:
    ChangeLogView: Public view that renders the dashboard changelog page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.views.change_log import ChangeLogView

        urlpatterns = [
            path("changelog/", ChangeLogView.as_view(), name="changelog"),
        ]
"""

from smarter.lib.django.views import (
    SmarterWebHtmlView,
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class ChangeLogView(SmarterWebHtmlView):
    """
    Public view that renders the dashboard changelog page.

    Extends :class:`~smarter.lib.django.views.SmarterWebHtmlView` and requires
    no authentication. Renders ``dashboard/changelog.html`` on a ``GET``
    request.

    Attributes:
        template_path (str): ``"dashboard/changelog.html"``
    """

    template_path = "dashboard/changelog.html"
