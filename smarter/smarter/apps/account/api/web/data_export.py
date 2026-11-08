"""
The user menu's Download My Data, under the console's account api, ``/api/web/account/data-export/``.

- ``GET data-export/``: what the dialog says before the user starts: the address that the link is emailed to,
  how long it works, how many exports are left today, and the latest export.
- ``POST data-export/``: start an export, or return the one in progress. See
  :func:`smarter.apps.account.data_export.start_data_export`.
- ``GET data-export/<id>/``: an export's progress, which the dialog polls.

Every response is camelCase JSON, from the Pydantic models of :mod:`smarter.apps.account.data_export`.
"""

from http import HTTPStatus

from django import http

from smarter.apps.account.data_export import (
    DataExportOverviewResponse,
    DataExportStartRefused,
    DataExportStatusResponse,
    start_data_export,
)
from smarter.apps.account.models import DataExport
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class DataExportView(SmarterAuthenticatedNeverCachedWebView):
    """
    Show the overview of the authenticated user's data exports (``GET``), or start one (``POST``).

    ``POST`` responds 202 with the new export's progress, or 200 with the export that is already in
    progress, or 429 with ``{"error": ...}`` when the user may not start one now.
    """

    def get(self, request, *args, **kwargs):
        """
        Return the overview of the user's data exports.

        :param request: The request.
        :returns: A json response, see :class:`~smarter.apps.account.data_export.DataExportOverviewResponse`.
        """
        overview = DataExportOverviewResponse.for_user(request.user)
        return http.JsonResponse(status=HTTPStatus.OK.value, data=overview.model_dump(mode="json"))

    def post(self, request, *args, **kwargs):
        """
        Start a data export, unless one is in progress.

        :param request: The request.
        :returns: A json response with the export's progress, see
            :class:`~smarter.apps.account.data_export.DataExportStatusResponse`.
        """
        try:
            export, started = start_data_export(request.user)
        except DataExportStartRefused as e:
            logger.info("%s.post() refused a data export for %s: %s", self.formatted_class_name, request.user, e)
            return http.JsonResponse(status=HTTPStatus.TOO_MANY_REQUESTS.value, data={"error": str(e)})
        status = HTTPStatus.ACCEPTED if started else HTTPStatus.OK
        progress = DataExportStatusResponse.from_model(export)
        return http.JsonResponse(status=status.value, data=progress.model_dump(mode="json"))


class DataExportDetailView(SmarterAuthenticatedNeverCachedWebView):
    """Return the progress of one of the authenticated user's data exports, which the dialog polls."""

    def get(self, request, *args, export_id: int = 0, **kwargs):
        """
        Return an export's progress.

        :param request: The request.
        :param export_id: The export's id.
        :returns: A json response with its progress, or 404 if the user has no such export.
        """
        export = DataExport.objects.filter(pk=export_id, user=request.user).select_related("user").first()
        if export is None:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"error": "Not found."})
        progress = DataExportStatusResponse.from_model(export)
        return http.JsonResponse(status=HTTPStatus.OK.value, data=progress.model_dump(mode="json"))
