"""
Cached reads of the doodle app's rows.

- :func:`doodle_of_the_day`: the doodle of a day in a region, for ``GET /api/v1/doodles/today/``.
- :func:`artwork_svg`: an artwork's SVG, for ``GET /api/v1/doodles/artwork/<sha256>.svg``.

A doodle is cached for :data:`~smarter.apps.doodle.const.DOODLE_CACHE_TIMEOUT` seconds, so a
change in the admin, e.g. an approval, shows within ten minutes. An artwork never changes: its name is its hash.
"""

import datetime

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
from .contract.models import DoodleOfTheDay
from .models import Doodle, DoodleArtwork, DoodleTheme
from .planner import candidates, default_theme

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


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
            "%s.doodle_of_the_day() no approved doodle for %s in %s: the calendar's.", logger_prefix, day, region
        )
        return doodle_from_theme(due[0], day, region, is_default=False)

    theme = default_theme()
    if theme is not None:
        logger.debug("%s.doodle_of_the_day() no approved doodle for %s in %s: the default.", logger_prefix, day, region)
        return doodle_from_theme(theme, day, region, is_default=True)

    logger.warning(
        "%s.doodle_of_the_day() the doodle themes aren't loaded. Run manage.py load_doodle_themes.", logger_prefix
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


__all__ = ["artwork_svg", "artwork_url", "doodle_of_the_day"]
