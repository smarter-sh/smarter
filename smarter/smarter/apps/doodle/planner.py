"""
The planner: it chooses the doodle of each day in each region, a week ahead.

For a day and a region, every active theme that is due and applies to the region is a candidate.
The candidate of the highest priority wins; at equal priority, a theme of the region's own wins
over one of every region, then the slug decides, so that the choice is the same on every run.
When nothing is due, the default theme wins.

A doodle that a person chose in the admin (source ``human``), or that the Smarter Doodle Editor
chose (source ``llm``, see :mod:`smarter.apps.doodle.editor`), is never replanned.
"""

import datetime
from typing import Optional

from django.db.models import QuerySet
from django.utils import timezone

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .const import DEFAULT_THEME_SLUG, PLANNING_DAYS, RETENTION_DAYS
from .models import (
    Doodle,
    DoodleArtwork,
    DoodleEditorRun,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)
from .regions import ALL_REGIONS, DoodleRegion, theme_applies_to

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)


def candidate_order(theme: DoodleTheme) -> tuple[int, int, str]:
    """
    Return the key that orders the candidates of a day, best first.

    :param theme: A candidate.
    :returns: Its sort key: higher priority, then regional, then slug.
    :rtype: tuple[int, int, str]
    """
    is_for_every_region = 1 if ALL_REGIONS in theme.regions else 0
    return (-theme.priority, is_for_every_region, theme.slug)


def themes_without_svg() -> QuerySet[DoodleTheme]:
    """
    Return the themes, with their artwork's hash, but not the SVG text that the planner never reads.

    :returns: A queryset of every theme.
    :rtype: QuerySet[DoodleTheme]
    """
    themes = DoodleTheme.objects.select_related("artwork").defer("props_svg", "artwork__svg")
    return themes


def catalog() -> list[DoodleTheme]:
    """
    Return the active themes of the catalog, without the default theme.

    The planner reads them once for all the days and regions it plans.

    :returns: The themes.
    :rtype: list[DoodleTheme]
    """
    themes = themes_without_svg().filter(is_active=True).exclude(slug=DEFAULT_THEME_SLUG)
    return list(themes)


def due_on(day: datetime.date, themes: Optional[list[DoodleTheme]] = None) -> list[DoodleTheme]:
    """
    Return the themes that are due on a day, in any region.

    :param day: The local date.
    :param themes: The catalog, from :func:`catalog`. Read now, by default.
    :returns: The themes whose schedule occurs on the day.
    :rtype: list[DoodleTheme]
    """
    if themes is None:
        themes = catalog()
    due = []
    for theme in themes:
        if theme.doodle_schedule.occurs_on(day):
            due.append(theme)
    return due


def candidates(day: datetime.date, region: str, due: Optional[list[DoodleTheme]] = None) -> list[DoodleTheme]:
    """
    Return the themes that are due on a day in a region, best first.

    :param day: The local date.
    :param region: The region.
    :param due: The themes due on the day, from :func:`due_on`, when the caller asks about
        several regions. Found now, by default.
    :returns: The themes, without the default theme.
    :rtype: list[DoodleTheme]
    """
    if due is None:
        due = due_on(day)
    found = []
    for theme in due:
        if theme_applies_to(theme.regions, region):
            found.append(theme)
    found.sort(key=candidate_order)
    return found


def default_theme() -> Optional[DoodleTheme]:
    """
    Return the default theme.

    :returns: The default theme, or ``None`` if the catalog isn't loaded.
    :rtype: Optional[DoodleTheme]
    """
    theme = themes_without_svg().filter(slug=DEFAULT_THEME_SLUG).first()
    return theme


def plan_doodle(day: datetime.date, region: str, due: Optional[list[DoodleTheme]] = None) -> Optional[Doodle]:
    """
    Plan the doodle of a day in a region.

    :param day: The local date.
    :param region: The region.
    :param due: The themes due on the day, from :func:`due_on`. Found now, by default.
    :returns: The doodle, or ``None`` if the catalog isn't loaded.
    :rtype: Optional[Doodle]
    """
    existing = Doodle.objects.filter(date=day, region=region).first()
    if existing is not None and existing.source in (DoodleSource.HUMAN, DoodleSource.LLM):
        logger.debug("%s.plan_doodle() keeps the doodle that %s chose: %s.", logger_prefix, existing.source, existing)
        return existing

    due = candidates(day, region, due=due)
    if due:
        theme = due[0]
        source = DoodleSource.CALENDAR
        others = [other.slug for other in due[1:]]
        reason = f"{theme.name} is due. Other candidates: {', '.join(others) or 'none'}."
    else:
        theme = default_theme()
        source = DoodleSource.DEFAULT
        reason = "Nothing is due."
    if theme is None:
        logger.warning(
            "%s.plan_doodle() found no default doodle theme. Run manage.py load_doodle_themes.", logger_prefix
        )
        return None

    doodle, _ = Doodle.objects.update_or_create(
        date=day,
        region=region,
        defaults={
            "theme": theme,
            "artwork": theme.artwork,
            "status": DoodleStatus.APPROVED,
            "source": source,
            "title": theme.name,
            "caption": theme.caption,
            "alt_text": theme.alt_text,
            "link_url": theme.link_url,
            "reason": reason,
        },
    )
    return doodle


def planning_window(days: int = PLANNING_DAYS, today: Optional[datetime.date] = None) -> list[datetime.date]:
    """
    Return the days to plan.

    The window starts the day before today in UTC, which is still today west of UTC, and ends
    ``days`` days after, which is already the day after east of UTC.

    :param days: How many days ahead to plan.
    :param today: Today, in UTC. Now, by default.
    :returns: The days.
    :rtype: list[datetime.date]
    """
    if today is None:
        today = timezone.now().date()
    first = today - datetime.timedelta(days=1)
    window = []
    for offset in range(days + 2):
        window.append(first + datetime.timedelta(days=offset))
    return window


def purge(today: Optional[datetime.date] = None, retention_days: int = RETENTION_DAYS) -> int:
    """
    Delete the doodles and editor runs older than the retention period, and the drawn themes and.

    artworks that nothing uses.

    :param today: Today, in UTC. Now, by default.
    :param retention_days: How many days of past doodles to keep.
    :returns: The number of doodles deleted.
    :rtype: int
    """
    if today is None:
        today = timezone.now().date()
    cutoff = today - datetime.timedelta(days=retention_days)
    deleted, _ = Doodle.objects.filter(date__lt=cutoff).delete()
    DoodleEditorRun.objects.filter(date__lt=cutoff).delete()
    DoodleTheme.objects.filter(is_generated=True, doodles__isnull=True).delete()
    unused = DoodleArtwork.objects.filter(themes__isnull=True, doodles__isnull=True)
    unused.delete()
    return deleted


def plan_doodles(days: int = PLANNING_DAYS, today: Optional[datetime.date] = None) -> int:
    """
    Plan the doodles of every region, ``days`` days ahead, and purge the old ones.

    :param days: How many days ahead to plan.
    :param today: Today, in UTC. Now, by default.
    :returns: The number of doodles planned.
    :rtype: int
    """
    planned = 0
    themes = catalog()
    for day in planning_window(days=days, today=today):
        due = due_on(day, themes)
        for region in DoodleRegion.values:
            doodle = plan_doodle(day, region, due=due)
            if doodle is not None:
                planned += 1
    deleted = purge(today=today)
    logger.info(
        "%s.plan_doodles() planned %s doodles, %s days ahead, and deleted %s old ones.",
        logger_prefix,
        planned,
        days,
        deleted,
    )
    return planned


__all__ = ["candidates", "catalog", "due_on", "plan_doodle", "plan_doodles", "planning_window", "purge"]
