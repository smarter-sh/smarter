"""
The REST api's Download My Data, under ``/api/v1/accounts/data-exports/``: what the web console's user menu does.

- ``GET data-exports/``: the overview: the address that the link is emailed to, how long it works, how many
  exports are left today, and the latest export.
- ``POST data-exports/``: start an export, or return the one in progress. The zip file of the user's
  manifests is built in the background, and a link to it is emailed to the user. See
  :func:`smarter.apps.account.data_export.start_data_export`.
- ``GET data-exports/<export_id>/``: an export's progress.

Every user may call them, for their own data. The responses are camelCase JSON, from the Pydantic models of
:mod:`smarter.apps.account.data_export`. Errors are Django REST framework's ``{"detail": ...}``.
"""

from http import HTTPStatus

from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.data_export import (
    DataExportOverviewResponse,
    DataExportStartRefused,
    DataExportStatusResponse,
    start_data_export,
)
from smarter.apps.account.models import DataExport, get_resolved_user
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class DataExportListView(SmarterAuthenticatedAPIView):
    """The overview of the user's data exports (``GET``), or start one (``POST``)."""

    def get(self, request: Request, *args, **kwargs) -> Response:
        """
        Return the overview of the user's data exports.

        :param request: The request.
        :returns: A :class:`~smarter.apps.account.data_export.DataExportOverviewResponse`.
        """
        user = get_resolved_user(request.user)
        overview = DataExportOverviewResponse.for_user(user)  # type: ignore[arg-type]
        return Response(overview.model_dump(mode="json"), status=HTTPStatus.OK)

    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        Start a data export, unless one is in progress.

        :param request: The request.
        :returns: The new export's progress, 202, or the one in progress, 200, or 429 when the user may not
            start one now: they have no email address, or started too many today.
        """
        user = get_resolved_user(request.user)
        try:
            export, started = start_data_export(user)  # type: ignore[arg-type]
        except DataExportStartRefused as e:
            logger.info("%s.post() refused a data export for user %s: %s", self.formatted_class_name, user.pk, e)  # type: ignore[union-attr]
            return Response({"detail": str(e)}, status=HTTPStatus.TOO_MANY_REQUESTS)
        if started:
            status = HTTPStatus.ACCEPTED
        else:
            status = HTTPStatus.OK
        progress = DataExportStatusResponse.from_model(export)
        return Response(progress.model_dump(mode="json"), status=status)


class DataExportView(SmarterAuthenticatedAPIView):
    """The progress of one of the user's data exports."""

    def get(self, request: Request, *args, export_id: int = 0, **kwargs) -> Response:
        """
        Return an export's progress.

        :param request: The request.
        :param export_id: The export's id.
        :returns: Its progress, or 404 if the user has no such export.
        """
        user = get_resolved_user(request.user)
        exports = DataExport.objects.filter(pk=export_id, user=user)  # type: ignore[misc]
        export = exports.select_related("user").first()
        if export is None:
            return Response({"detail": f"You have no data export {export_id}."}, status=HTTPStatus.NOT_FOUND)
        progress = DataExportStatusResponse.from_model(export)
        return Response(progress.model_dump(mode="json"), status=HTTPStatus.OK)


__all__ = ["DataExportListView", "DataExportView"]
