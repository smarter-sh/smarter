"""
The schedule of a doodle theme: on which days it is due.

A theme's ``schedule`` is one of:

- ``fixed``: the same day every year, e.g. Pi Day on March 14, for ``days`` days.
- ``nth_weekday``: e.g. Ada Lovelace Day, the second Tuesday of October.
- ``holiday``: a holiday of a country, by name, from the ``holidays`` package, which knows the
  moving ones: Diwali, the Lunar New Year, Eid al-Fitr, Hanukkah, Thanksgiving, ...
- ``never``: the evergreen default theme, which the planner chooses when nothing else is due.
"""

import calendar
import datetime
import warnings
from typing import Literal, Optional

import holidays
from cache_results import cache_results
from pydantic import BaseModel, ConfigDict, Field, model_validator

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

HOLIDAY_CACHE_TIMEOUT = 60 * 60 * 24
"""Seconds that a country's holidays of one year are cached."""

OBSERVED = "(observed)"
"""The suffix of a holiday's name on the weekday that replaces a weekend, which isn't the holiday."""


@cache_results(timeout=HOLIDAY_CACHE_TIMEOUT)
def country_holidays(country: str, year: int) -> dict[str, list[str]]:
    """
    Return a country's holidays in a year, by date.

    Every category of the country's holidays is included (public, optional, school, ...), because
    some holidays that a doodle celebrates aren't public ones, e.g. Hanukkah in Israel. The weekdays
    that replace a holiday on a weekend, "(observed)", are left out: they aren't the holiday.

    :param country: The ISO 3166 country code, e.g. ``IN``.
    :param year: The year.
    :returns: The English names of each date's holidays, by ISO date, e.g.
        ``{"2026-11-08": ["Diwali"]}``. Empty if the country isn't supported, or the package
        doesn't date that year.
    :rtype: dict[str, list[str]]
    """
    try:
        country_class = holidays.country_holidays(country).__class__
    except NotImplementedError:
        logger.warning("%s.country_holidays() the holidays package doesn't support %s.", logger_prefix, country)
        return {}
    categories = country_class.supported_categories
    with warnings.catch_warnings():
        # e.g. "Requested Holidays are available only from 2001 to 2035.": the year is empty then.
        warnings.simplefilter("ignore", UserWarning)
        calendar_of_the_year = holidays.country_holidays(country, years=year, language="en_US", categories=categories)
    by_date: dict[str, list[str]] = {}
    for day, holiday_names in sorted(calendar_of_the_year.items()):
        names = []
        for holiday_name in holiday_names.split("; "):
            if OBSERVED in holiday_name:
                continue
            names.append(holiday_name)
        if names:
            by_date[day.isoformat()] = names
    return by_date


def holiday_dates(country: str, name: str, year: int) -> list[str]:
    """
    Return the dates of a country's holiday in a year.

    :param country: The ISO 3166 country code, e.g. ``IN``.
    :param name: Text that the holiday's English name contains, e.g. ``Diwali``. Case doesn't matter.
    :param year: The year.
    :returns: The dates, as ISO strings, e.g. ``["2026-11-08"]``. Empty if the country isn't
        supported, or has no such holiday that year.
    :rtype: list[str]
    """
    wanted = name.lower()
    dates: list[str] = []
    for iso_date, names in country_holidays(country, year).items():
        for holiday_name in names:
            if wanted in holiday_name.lower():
                dates.append(iso_date)
                break
    return dates


def holidays_on(country: str, day: datetime.date) -> list[str]:
    """
    Return the holidays of a country on a day.

    :param country: The ISO 3166 country code, e.g. ``MX``.
    :param day: The day.
    :returns: The holidays' English names, e.g. ``["Revolution Day"]``.
    :rtype: list[str]
    """
    by_date = country_holidays(country, day.year)
    names = by_date.get(day.isoformat(), [])
    return names


def nth_weekday(year: int, month: int, weekday: int, nth: int) -> datetime.date:
    """
    Return the nth weekday of a month.

    :param year: The year.
    :param month: The month, 1 to 12.
    :param weekday: The weekday, 0 (Monday) to 6 (Sunday).
    :param nth: 1 to 5, or -1 for the last one.
    :returns: The date, e.g. the second Tuesday of October 2026 is 2026-10-13.
    :rtype: datetime.date
    :raises ValueError: If the month has no such weekday, e.g. a fifth Monday.
    """
    weeks = calendar.monthcalendar(year, month)
    days = []
    for week in weeks:
        day = week[weekday]
        if day != 0:
            days.append(day)
    if nth == -1:
        return datetime.date(year, month, days[-1])
    if nth > len(days):
        raise ValueError(f"{year}-{month} has no weekday {weekday} number {nth}.")
    return datetime.date(year, month, days[nth - 1])


class DoodleSchedule(BaseModel):
    """When a doodle theme is due.

    See :mod:`smarter.apps.doodle.schedule`.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["fixed", "nth_weekday", "holiday", "never"] = Field(description="How the dates are found.")
    month: Optional[int] = Field(default=None, ge=1, le=12, description="The month, for fixed and nth_weekday.")
    day: Optional[int] = Field(default=None, ge=1, le=31, description="The day of the month, for fixed.")
    weekday: Optional[int] = Field(
        default=None, ge=0, le=6, description="The weekday, 0 (Monday) to 6 (Sunday), for nth_weekday."
    )
    nth: Optional[int] = Field(default=None, ge=-1, le=5, description="Which weekday, 1 to 5 or -1 for the last.")
    country: Optional[str] = Field(
        default=None, min_length=2, max_length=2, description="The ISO 3166 country code, for holiday."
    )
    holiday: Optional[str] = Field(default=None, min_length=2, description="Text the holiday's name contains.")
    days: int = Field(default=1, ge=1, le=14, description="How many days the theme lasts, from each date.")

    @model_validator(mode="after")
    def check_fields_of_kind(self) -> "DoodleSchedule":
        """
        Check that the schedule has the fields that its kind needs.

        :returns: The schedule.
        :raises ValueError: If a field that the kind needs is missing.
        """
        required: dict[str, list[str]] = {
            "fixed": ["month", "day"],
            "nth_weekday": ["month", "weekday", "nth"],
            "holiday": ["country", "holiday"],
            "never": [],
        }
        for field_name in required[self.kind]:
            if getattr(self, field_name) is None:
                raise ValueError(f"A {self.kind} schedule needs {field_name}.")
        if self.nth == 0:
            raise ValueError("nth is 1 to 5, or -1 for the last weekday of the month.")
        return self

    def start_dates(self, year: int) -> list[datetime.date]:
        """
        Return the dates on which the theme starts in a year.

        :param year: The year.
        :returns: The dates. Empty for ``never``, or a date that the year doesn't have (February 29).
        :rtype: list[datetime.date]
        """
        if self.kind == "fixed":
            try:
                return [datetime.date(year, self.month, self.day)]  # type: ignore[arg-type]
            except ValueError:
                return []
        if self.kind == "nth_weekday":
            try:
                return [nth_weekday(year, self.month, self.weekday, self.nth)]  # type: ignore[arg-type]
            except ValueError:
                return []
        if self.kind == "holiday":
            iso_dates = holiday_dates(str(self.country).upper(), str(self.holiday), year)
            return [datetime.date.fromisoformat(iso_date) for iso_date in iso_dates]
        return []

    def occurs_on(self, day: datetime.date) -> bool:
        """
        Whether the theme is due on a day.

        A theme that lasts several days, e.g. from December 24, may have started the year before.

        :param day: The day.
        :returns: True if the theme is due.
        :rtype: bool
        """
        for year in (day.year - 1, day.year):
            for start in self.start_dates(year):
                end = start + datetime.timedelta(days=self.days)
                if start <= day < end:
                    return True
        return False


__all__ = ["DoodleSchedule", "country_holidays", "holiday_dates", "holidays_on", "nth_weekday"]
