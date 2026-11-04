"""
The regions of the doodle, and how a browser's time zone maps to one.

A browser sends its IANA time zone (``Intl.DateTimeFormat().resolvedOptions().timeZone``), e.g.
``America/Vancouver``. The time zone gives the visitor's local date, so that a holiday starts at
local midnight, and, through the tz database's ``zone.tab``, the country, which gives the region.
No IP address is looked up, and nothing is stored.

The regions are coarse on purpose: each one is a doodle to plan every day.
"""

import datetime
import importlib.resources
from functools import lru_cache
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import models
from django.utils import timezone


class DoodleRegion(models.TextChoices):
    """A region that sees its own doodle."""

    GLOBAL = "global", "Global"
    US = "us", "United States"
    CA = "ca", "Canada"
    MX = "mx", "Mexico"
    LATAM = "latam", "Latin America and the Caribbean"
    EUROPE = "europe", "Europe"
    AFRICA = "africa", "Africa"
    MIDDLE_EAST = "middle-east", "Middle East"
    SOUTH_ASIA = "south-asia", "South Asia"
    EAST_ASIA = "east-asia", "East Asia"
    SOUTHEAST_ASIA = "southeast-asia", "Southeast Asia"
    OCEANIA = "oceania", "Oceania"


ALL_REGIONS = "*"
"""In a theme's ``regions``, every region."""

COUNTRY_REGIONS: dict[str, DoodleRegion] = {
    "US": DoodleRegion.US,
    "CA": DoodleRegion.CA,
    "MX": DoodleRegion.MX,
    # the Middle East
    "AE": DoodleRegion.MIDDLE_EAST,
    "BH": DoodleRegion.MIDDLE_EAST,
    "CY": DoodleRegion.MIDDLE_EAST,
    "IL": DoodleRegion.MIDDLE_EAST,
    "IQ": DoodleRegion.MIDDLE_EAST,
    "IR": DoodleRegion.MIDDLE_EAST,
    "JO": DoodleRegion.MIDDLE_EAST,
    "KW": DoodleRegion.MIDDLE_EAST,
    "LB": DoodleRegion.MIDDLE_EAST,
    "OM": DoodleRegion.MIDDLE_EAST,
    "PS": DoodleRegion.MIDDLE_EAST,
    "QA": DoodleRegion.MIDDLE_EAST,
    "SA": DoodleRegion.MIDDLE_EAST,
    "SY": DoodleRegion.MIDDLE_EAST,
    "TR": DoodleRegion.MIDDLE_EAST,
    "YE": DoodleRegion.MIDDLE_EAST,
    # South Asia
    "AF": DoodleRegion.SOUTH_ASIA,
    "BD": DoodleRegion.SOUTH_ASIA,
    "BT": DoodleRegion.SOUTH_ASIA,
    "IN": DoodleRegion.SOUTH_ASIA,
    "LK": DoodleRegion.SOUTH_ASIA,
    "MV": DoodleRegion.SOUTH_ASIA,
    "NP": DoodleRegion.SOUTH_ASIA,
    "PK": DoodleRegion.SOUTH_ASIA,
    # East Asia
    "CN": DoodleRegion.EAST_ASIA,
    "HK": DoodleRegion.EAST_ASIA,
    "JP": DoodleRegion.EAST_ASIA,
    "KP": DoodleRegion.EAST_ASIA,
    "KR": DoodleRegion.EAST_ASIA,
    "MN": DoodleRegion.EAST_ASIA,
    "MO": DoodleRegion.EAST_ASIA,
    "TW": DoodleRegion.EAST_ASIA,
    # Southeast Asia
    "BN": DoodleRegion.SOUTHEAST_ASIA,
    "ID": DoodleRegion.SOUTHEAST_ASIA,
    "KH": DoodleRegion.SOUTHEAST_ASIA,
    "LA": DoodleRegion.SOUTHEAST_ASIA,
    "MM": DoodleRegion.SOUTHEAST_ASIA,
    "MY": DoodleRegion.SOUTHEAST_ASIA,
    "PH": DoodleRegion.SOUTHEAST_ASIA,
    "SG": DoodleRegion.SOUTHEAST_ASIA,
    "TH": DoodleRegion.SOUTHEAST_ASIA,
    "TL": DoodleRegion.SOUTHEAST_ASIA,
    "VN": DoodleRegion.SOUTHEAST_ASIA,
    # Oceania, whose Pacific islands the time zone prefix covers
    "AU": DoodleRegion.OCEANIA,
    "NZ": DoodleRegion.OCEANIA,
}
"""The countries whose region their time zone's continent doesn't decide, e.g. Asia's four regions."""

CONTINENT_REGIONS: dict[str, DoodleRegion] = {
    "America": DoodleRegion.LATAM,
    "Europe": DoodleRegion.EUROPE,
    "Africa": DoodleRegion.AFRICA,
    "Australia": DoodleRegion.OCEANIA,
    "Pacific": DoodleRegion.OCEANIA,
}
"""
The region of a country that :data:`COUNTRY_REGIONS` doesn't list, by its time zone's first part.

The United States, Canada and Mexico are listed, so the rest of ``America/`` is Latin America and
the Caribbean. A time zone of any other continent, e.g. Central Asia's, or ``UTC``, is global.
"""


def load_zone_countries() -> dict[str, str]:
    """
    Read the tz database's ``zone.tab``: the country of each canonical time zone.

    :returns: The country code of each time zone, e.g. ``{"America/Vancouver": "CA"}``.
    :rtype: dict[str, str]
    """
    zoneinfo_folder = importlib.resources.files("tzdata").joinpath("zoneinfo")
    text = zoneinfo_folder.joinpath("zone.tab").read_text(encoding="utf-8")
    countries: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        columns = line.split("\t")
        if len(columns) < 3:
            continue
        country = columns[0]
        zone = columns[2]
        countries[zone] = country
    return countries


ZONE_COUNTRIES: dict[str, str] = load_zone_countries()
"""The country code of each canonical time zone, from the ``tzdata`` package."""


def valid_timezone(tz: Optional[str]) -> Optional[ZoneInfo]:
    """
    Return the time zone of an IANA name, or ``None`` if the name isn't one.

    :param tz: An IANA time zone name, e.g. ``Europe/Paris``, from the browser.
    :returns: The time zone, or ``None``.
    :rtype: Optional[ZoneInfo]
    """
    if not tz:
        return None
    if len(tz) > 64:
        return None
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def country_for_timezone(tz: Optional[str]) -> Optional[str]:
    """
    Return the country of a time zone.

    :param tz: An IANA time zone name, e.g. ``America/Mexico_City``.
    :returns: The ISO 3166 country code, e.g. ``MX``, or ``None`` for a time zone that belongs to
        no country, such as ``UTC``, or to none in ``zone.tab``, such as the alias ``US/Pacific``.
    :rtype: Optional[str]
    """
    if not tz:
        return None
    return ZONE_COUNTRIES.get(tz)


def region_for_timezone(tz: Optional[str]) -> DoodleRegion:
    """
    Return the region of a time zone.

    :param tz: An IANA time zone name, e.g. ``Asia/Kolkata``.
    :returns: The region, e.g. :attr:`DoodleRegion.SOUTH_ASIA`, or :attr:`DoodleRegion.GLOBAL`.
    :rtype: DoodleRegion
    """
    if valid_timezone(tz) is None:
        return DoodleRegion.GLOBAL
    country = country_for_timezone(tz)
    if country in COUNTRY_REGIONS:
        return COUNTRY_REGIONS[country]
    continent = str(tz).split("/", maxsplit=1)[0]
    region = CONTINENT_REGIONS.get(continent, DoodleRegion.GLOBAL)
    return region


def local_date(tz: Optional[str], now: Optional[datetime.datetime] = None) -> datetime.date:
    """
    Return the date in a time zone.

    :param tz: An IANA time zone name. An invalid name is UTC.
    :param now: The moment. Now, by default.
    :returns: The date in that time zone at that moment.
    :rtype: datetime.date
    """
    if now is None:
        now = timezone.now()
    zone = valid_timezone(tz)
    if zone is None:
        zone = ZoneInfo("UTC")
    local_now = now.astimezone(zone)
    return local_now.date()


@lru_cache(maxsize=32)
def region_countries(region: str) -> tuple[str, ...]:
    """
    Return the countries of a region, by their time zones.

    It is a pure function of the tz database, which the editor asks again for every region of
    every day, so its answers are kept for the life of the process.

    :param region: The region.
    :returns: The ISO 3166 country codes whose time zones belong to the region, sorted. Empty for
        :attr:`DoodleRegion.GLOBAL`, which is no country's.
    :rtype: tuple[str, ...]
    """
    countries = set()
    if region == DoodleRegion.GLOBAL:
        return ()
    for zone, country in ZONE_COUNTRIES.items():
        if region_for_timezone(zone) == region:
            countries.add(country)
    # a tuple, so that no caller can change the cached answer.
    found = tuple(sorted(countries))
    return found


def theme_applies_to(regions: list[str], region: str) -> bool:
    """
    Whether a theme whose ``regions`` are these is shown in a region.

    :param regions: The theme's regions, or ``["*"]`` for all of them.
    :param region: The region.
    :returns: True if the theme applies to the region.
    :rtype: bool
    """
    if ALL_REGIONS in regions:
        return True
    return region in regions


__all__ = [
    "ALL_REGIONS",
    "DoodleRegion",
    "country_for_timezone",
    "local_date",
    "region_countries",
    "region_for_timezone",
    "theme_applies_to",
    "valid_timezone",
]
