# pylint: disable=W0613
"""
The views of the doodle api, ``/api/v1/doodles/``.

Both are public, because the sign-in page shows the doodle before anyone signs in. Neither reads
or writes anything of the visitor's: the time zone that the browser sends picks the region and the
local date, and is not stored. Their reads are cached in :mod:`smarter.apps.doodle.caching`.

- ``today/?tz=<IANA time zone>``: :class:`DoodleTodayView`, the doodle of the day, as JSON.
- ``artwork/<sha256>.svg``: :class:`DoodleArtworkView`, an artwork, cached forever by browsers.
"""

from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.doodle.artwork import still_svg
from smarter.apps.doodle.caching import artwork_svg, doodle_of_the_day
from smarter.apps.doodle.const import ARTWORK_CACHE_MAX_AGE, TODAY_CACHE_MAX_AGE
from smarter.apps.doodle.contract.models import DoodleApiResponse
from smarter.apps.doodle.regions import DoodleRegion, local_date, region_for_timezone
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active
from smarter.lib.drf.views.helpers import SmarterUnauthenticatedAPIView

ARTWORK_CONTENT_SECURITY_POLICY = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
"""
The policy of an artwork opened on its own, as a page: no scripts, nothing loaded.

In ``<img>``, as the sign-in page shows it, an SVG can't run scripts anyway.
"""


class DoodleTodayView(SmarterUnauthenticatedAPIView):
    """
    The doodle of the day, for the sign-in page.

    ``GET`` with the query parameter ``tz``, the browser's IANA time zone, e.g. ``Asia/Kolkata``.
    It picks the visitor's region and local date. Without it, or while the
    ``enable_doodle_regional`` switch is off, the doodle is the global one.
    """

    def get(self, request: Request, *args, **kwargs) -> Response:
        """
        Return the doodle of the day.

        :param request: The request.
        :returns: A :class:`~smarter.apps.doodle.contract.models.DoodleApiResponse`.
        :rtype: Response
        """
        tz = request.query_params.get("tz")
        region = DoodleRegion.GLOBAL
        if switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_REGIONAL):
            region = region_for_timezone(tz)
        day = local_date(tz)
        doodle = doodle_of_the_day(day.isoformat(), str(region))

        animated = switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_ANIMATION)
        show_caption = switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_CAPTION)
        show_ai_credit = switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_AI_CREDIT)
        body = DoodleApiResponse.from_doodle(
            doodle, animated=animated, show_caption=show_caption, show_ai_credit=show_ai_credit
        )

        response = Response(body.to_json())
        response["Cache-Control"] = f"public, max-age={TODAY_CACHE_MAX_AGE}"
        return response


class DoodleArtworkView(SmarterUnauthenticatedAPIView):
    """
    An artwork of a doodle, ``image/svg+xml``.

    Its url names its content's hash, so browsers may cache it forever. With ``?still=1``, it has
    no animations.
    """

    def get(self, request: Request, sha256: str, *args, **kwargs) -> HttpResponse:
        """
        Return the artwork.

        :param request: The request.
        :param sha256: The artwork's hash.
        :returns: The SVG.
        :rtype: HttpResponse
        :raises NotFound: If there is no such artwork.
        """
        svg = artwork_svg(sha256.lower())
        still = request.query_params.get("still")
        if still:
            svg = still_svg(svg)
        response = HttpResponse(svg, content_type="image/svg+xml")
        response["Cache-Control"] = f"public, max-age={ARTWORK_CACHE_MAX_AGE}, immutable"
        response["Content-Security-Policy"] = ARTWORK_CONTENT_SECURITY_POLICY
        response["X-Content-Type-Options"] = "nosniff"
        return response


__all__ = ["DoodleArtworkView", "DoodleTodayView"]
