"""
The manifest drop zone page: the single-page console's (ADR-035).

The console renders ``@smarter/drop-zone`` at ``/dashboard/dropzone``, and the page applies each manifest dropped
on it with the public api's ``/api/v1/cli/apply/``. Django keeps :class:`DropzoneView` at the path it served the
page at, so that the url name ``dashboard:dropzone:dropzone_view`` still reverses.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.dropzone.view import DropzoneView

        urlpatterns = [
            path("", DropzoneView.as_view(), name="dropzone_view"),
        ]
"""

from smarter.apps.dashboard.views.console_app import ConsoleAppView


class DropzoneView(ConsoleAppView):
    """
    The manifest drop zone page, ``/dashboard/dropzone/``: the single-page console's.

    The page exists only while ``smarter_settings.enable_dropzone_manifest_apply`` is set: otherwise its url is not
    registered, and the console's session says that the page is off, so that the console shows its Page not found.
    """
