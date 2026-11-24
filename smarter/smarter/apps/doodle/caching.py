"""
Cached reads of the doodle app's rows.

- :func:`doodle_of_the_day`: the doodle of a day in a region, for ``GET /api/v1/doodles/today/``.
- :func:`artwork_svg`: an artwork's SVG, for ``GET /api/v1/doodles/artwork/<sha256>.svg``.
- :func:`approved_doodle`: the approved doodle of a day in a region, for
  ``GET /api/v1/doodles/<date>/<region>/``.
- :func:`newest_drawn_doodles`: the newest doodles that the Smarter Doodle Artist drew, for the
  dashboard's Newest Doodles widget.

A doodle is cached for :data:`~smarter.apps.doodle.const.DOODLE_CACHE_TIMEOUT` seconds, so a
change in the admin, e.g. an approval, shows within ten minutes. An artwork never changes: its name is its hash.
"""

import datetime
from typing import Optional

from cache_results import cache_results
from django.templatetags.static import static
from rest_framework.exceptions import NotFound

from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .const import (
    ARTWORK_CACHE_MAX_AGE,
    BASE_SCENE_STATIC_PATH,
    DEFAULT_THEME_SLUG,
    DOODLE_CACHE_TIMEOUT,
)
from .contract.models import DoodleOfTheDay, DrawnDoodle, with_query
from .models import Doodle, DoodleArtwork, DoodleStatus, DoodleTheme
from .planner import candidates, default_theme
from .regions import DoodleRegion

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)


def artwork_url(sha256: str) -> str:
    """
    Return the url of an artwork.

    :param sha256: The artwork's hash.
    :returns: Its path, e.g. ``/api/v1/doodles/artwork/<sha256>.svg``.
    :rtype: str
    """
    # pylint: disable=import-outside-toplevel
    from .api.v1.urls import DoodleApiV1ReverseViews  # its views import this module

    path = reverse(
        f"{DoodleApiV1ReverseViews.namespace}:{DoodleApiV1ReverseViews.artwork}",
        kwargs={"sha256": sha256},
    )
    return path


def doodle_from_row(doodle: Doodle, region: str) -> DoodleOfTheDay:
    """
    Return the doodle of the day of a planned doodle.

    :param doodle: The planned doodle.
    :param region: The visitor's region, which may be another than the doodle's (its fallback).
    :returns: The doodle of the day.
    :rtype: DoodleOfTheDay
    """
    # the editor may choose the default too, so it is the theme, not the source, that says.
    is_default = doodle.theme.slug == DEFAULT_THEME_SLUG
    return DoodleOfTheDay(
        date=doodle.date.isoformat(),
        region=region,
        theme=doodle.theme.slug,
        title=doodle.title,
        caption=doodle.caption,
        alt_text=doodle.alt_text,
        link_url=doodle.link_url,
        image_url=artwork_url(doodle.artwork.sha256),
        is_default=is_default,
        ai_credit=doodle.ai_credit,
    )


def doodle_from_theme(theme: DoodleTheme, day: str, region: str, is_default: bool) -> DoodleOfTheDay:
    """
    Return the doodle of the day of a theme, when no doodle is approved.

    :param theme: The theme: the calendar's choice, or the default theme.
    :param day: The local date.
    :param region: The visitor's region.
    :param is_default: Whether it is the default theme.
    :returns: The doodle of the day.
    :rtype: DoodleOfTheDay
    """
    return DoodleOfTheDay(
        date=day,
        region=region,
        theme=theme.slug,
        title=theme.name,
        caption=theme.caption,
        alt_text=theme.alt_text,
        link_url=theme.link_url,
        image_url=artwork_url(theme.artwork.sha256),
        is_default=is_default,
    )


@cache_results(timeout=DOODLE_CACHE_TIMEOUT)
def doodle_of_the_day(day: str, region: str) -> DoodleOfTheDay:
    """
    Return the doodle of a day in a region.

    The region's approved doodle; else, e.g. while a drawn doodle awaits approval, or before the
    planner has run, the calendar's choice for the region, made now; else, when the catalog isn't
    loaded, the base scene from the static files.

    :param day: The local date, as an ISO string.
    :param region: The region.
    :returns: The doodle of the day.
    :rtype: DoodleOfTheDay
    """
    date = datetime.date.fromisoformat(day)
    doodle = Doodle.shown(date, region)
    if doodle is not None:
        return doodle_from_row(doodle, region)

    due = candidates(date, region)
    if due:
        logger.debug(
            "no approved doodle for %s in %s: the calendar's.",
            day,
            region,
        )
        return doodle_from_theme(due[0], day, region, is_default=False)

    theme = default_theme()
    if theme is not None:
        logger.debug(
            "no approved doodle for %s in %s: the default.",
            day,
            region,
        )
        return doodle_from_theme(theme, day, region, is_default=True)

    logger.warning(
        "the doodle themes aren't loaded. Run manage.py load_doodle_themes.",
    )
    return DoodleOfTheDay(
        date=day,
        region=region,
        theme="default",
        title="The Smarter Project",
        caption="",
        alt_text="A Smarter LLMClient's chat window, and the plugin, guardrail, vectorstore and secret around it.",
        link_url="",
        image_url=static(BASE_SCENE_STATIC_PATH),
        is_default=True,
    )


@cache_results(timeout=DOODLE_CACHE_TIMEOUT)
def approved_doodle(day: str, region: str) -> Optional[DoodleOfTheDay]:
    """
    Return the approved doodle of a day in a region, as the sign-in page showed it, or None.

    Unlike :func:`doodle_of_the_day`, nothing takes its place when there is none: it is for a page that
    shows one doodle, e.g. from the dashboard's Newest Doodles widget.

    :param day: The local date, as an ISO string.
    :param region: The region.
    :returns: The doodle, or None if none was approved.
    :rtype: Optional[DoodleOfTheDay]
    """
    date = datetime.date.fromisoformat(day)
    doodle = Doodle.shown(date, region)
    if doodle is None:
        return None
    retval = doodle_from_row(doodle, region)
    return retval


@cache_results(timeout=DOODLE_CACHE_TIMEOUT)
def newest_drawn_doodles(today: str, limit: int) -> list[DrawnDoodle]:
    """
    Return the newest approved doodles that the Smarter Doodle Artist drew, up to a day.

    A doodle of a later day isn't shown before its day. Each artwork is still, without animations.

    :param today: The last day, as an ISO string, e.g. today's date in UTC. It is part of the
        cache's key, so the list moves on every day.
    :param limit: How many doodles, at most.
    :returns: The doodles, the newest first, then by region.
    :rtype: list[DrawnDoodle]
    """
    last_day = datetime.date.fromisoformat(today)
    rows = (
        Doodle.objects.select_related("theme", "artwork")
        .defer("theme__props_svg", "artwork__svg")
        .filter(status=DoodleStatus.APPROVED, theme__is_generated=True, date__lte=last_day)
        .order_by("-date", "region")[:limit]
    )
    doodles = []
    for row in rows:
        doodle = doodle_from_row(row, row.region)
        fields = doodle.model_dump(by_alias=False)
        fields["image_url"] = with_query(doodle.image_url, "still=1")
        region_name = str(DoodleRegion(row.region).label)
        drawn = DrawnDoodle(**fields, region_name=region_name)
        doodles.append(drawn)
    return doodles


@cache_results(timeout=ARTWORK_CACHE_MAX_AGE)
def artwork_svg(sha256: str) -> str:
    """
    Return the SVG of an artwork.

    :param sha256: The artwork's hash.
    :returns: Its SVG.
    :rtype: str
    :raises NotFound: If there is no such artwork. The failure isn't cached.
    """
    artwork = DoodleArtwork.objects.filter(sha256=sha256).first()
    if artwork is None:
        raise NotFound("No such doodle artwork.")
    return str(artwork.svg)


__all__ = ["approved_doodle", "artwork_svg", "artwork_url", "doodle_of_the_day", "newest_drawn_doodles"]
