# pylint: disable=W0613
"""
API view for the dashboard's Newest Doodles widget: the newest doodles that the Smarter Doodle.

Artist drew for the sign-in page, in any region.

The doodles are read by :func:`smarter.apps.doodle.caching.newest_drawn_doodles`: only approved
ones, up to today, so a doodle that awaits a superuser's approval, or one of a later day, is never
shown. Every user sees the same doodles. Each links to its artwork, a public url, and to the page
that its caption links to.

- :class:`NewestDoodlesView`: the authenticated POST endpoint, which returns a
  :class:`~smarter.apps.doodle.contract.models.DrawnDoodlesResponse`.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse
from django.utils import timezone

from smarter.apps.doodle.caching import newest_drawn_doodles
from smarter.apps.doodle.const import NEWEST_DRAWN_DOODLES
from smarter.apps.doodle.contract.models import DrawnDoodlesResponse
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedWebView

logger = logging.getSmarterLogger(__name__)


class NewestDoodlesView(SmarterAuthenticatedWebView):
    """
    API view for the dashboard's Newest Doodles widget.

    A ``POST`` returns the newest doodles that the Smarter Doodle Artist drew, at most
    :data:`~smarter.apps.doodle.const.NEWEST_DRAWN_DOODLES`, the newest first.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to return the newest drawn doodles.

        :param request: The incoming HTTP POST request. Its body is ignored.
        :type request: django.http.HttpRequest
        :returns: A :class:`~smarter.apps.doodle.contract.models.DrawnDoodlesResponse`.
        :rtype: django.http.JsonResponse
        """
        today = timezone.now().date().isoformat()
        doodles = newest_drawn_doodles(today, NEWEST_DRAWN_DOODLES)
        logger.debug("%s drawn doodles up to %s.", len(doodles), today)
        response = DrawnDoodlesResponse(doodles=doodles)
        return JsonResponse(response.to_json(), status=HTTPStatus.OK)
