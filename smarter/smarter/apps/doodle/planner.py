"""
The planner: it chooses the doodle of each day in each region, a week ahead.

For a day and a region, every active theme that is due and applies to the region is a candidate.
The candidate of the highest priority wins; at equal priority, a theme of the region's own wins
over one of every region, then the slug decides, so that the choice is the same on every run.
When nothing is due, the default theme wins.

A doodle that a person chose in the admin (source ``human``) is never replanned.
"""

import datetime
from typing import Optional

from django.utils import timezone

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .const import DEFAULT_THEME_SLUG, PLANNING_DAYS, RETENTION_DAYS
from .models import (
    Doodle,
    DoodleArtwork,
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


def candidates(day: datetime.date, region: str) -> list[DoodleTheme]:
    """
    Return the themes that are due on a day in a region, best first.

    :param day: The local date.
    :param region: The region.
    :returns: The themes, without the default theme.
    :rtype: list[DoodleTheme]
    """
    due = []
    themes = DoodleTheme.objects.filter(is_active=True).exclude(slug=DEFAULT_THEME_SLUG)
    for theme in themes:
        if not theme_applies_to(theme.regions, region):
            continue
        if not theme.doodle_schedule.occurs_on(day):
            continue
        due.append(theme)
    due.sort(key=candidate_order)
    return due


def default_theme() -> Optional[DoodleTheme]:
    """
    Return the default theme.

    :returns: The default theme, or ``None`` if the catalog isn't loaded.
    :rtype: Optional[DoodleTheme]
    """
    return DoodleTheme.objects.filter(slug=DEFAULT_THEME_SLUG).select_related("artwork").first()


def plan_doodle(day: datetime.date, region: str) -> Optional[Doodle]:
    """
    Plan the doodle of a day in a region.

    :param day: The local date.
    :param region: The region.
    :returns: The doodle, or ``None`` if the catalog isn't loaded.
    :rtype: Optional[Doodle]
    """
    existing = Doodle.objects.filter(date=day, region=region).first()
    if existing is not None and existing.source == DoodleSource.HUMAN:
        logger.debug("%s.plan_doodle() keeps the doodle that a person chose: %s.", logger_prefix, existing)
        return existing

    due = candidates(day, region)
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
    Delete the doodles older than the retention period, and the artworks that nothing uses.

    :param today: Today, in UTC. Now, by default.
    :param retention_days: How many days of past doodles to keep.
    :returns: The number of doodles deleted.
    :rtype: int
    """
    if today is None:
        today = timezone.now().date()
    cutoff = today - datetime.timedelta(days=retention_days)
    deleted, _ = Doodle.objects.filter(date__lt=cutoff).delete()
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
    for day in planning_window(days=days, today=today):
        for region in DoodleRegion.values:
            doodle = plan_doodle(day, region)
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


__all__ = ["candidates", "plan_doodle", "plan_doodles", "planning_window", "purge"]
