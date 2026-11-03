"""Test :mod:`smarter.apps.doodle.schedule`."""

import datetime
from unittest.mock import patch

from pydantic import ValidationError

from smarter.apps.doodle import schedule
from smarter.apps.doodle.schedule import DoodleSchedule, holiday_dates, nth_weekday
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSchedule(SmarterTestBase):
    """A theme's schedule says on which days it is due."""

    def test_fixed(self):
        pi_day = DoodleSchedule(kind="fixed", month=3, day=14)
        self.assertTrue(pi_day.occurs_on(datetime.date(2027, 3, 14)))
        self.assertFalse(pi_day.occurs_on(datetime.date(2027, 3, 15)))

    def test_fixed_for_several_days_across_the_new_year(self):
        holidays = DoodleSchedule(kind="fixed", month=12, day=31, days=3)
        self.assertTrue(holidays.occurs_on(datetime.date(2027, 1, 2)))
        self.assertFalse(holidays.occurs_on(datetime.date(2027, 1, 3)))

    def test_fixed_on_a_day_that_a_year_lacks(self):
        leap_day = DoodleSchedule(kind="fixed", month=2, day=29)
        self.assertEqual(leap_day.start_dates(2027), [])
        self.assertTrue(leap_day.occurs_on(datetime.date(2028, 2, 29)))

    def test_nth_weekday(self):
        ada_lovelace_day = DoodleSchedule(kind="nth_weekday", month=10, weekday=1, nth=2)
        self.assertEqual(ada_lovelace_day.start_dates(2026), [datetime.date(2026, 10, 13)])
        self.assertTrue(ada_lovelace_day.occurs_on(datetime.date(2026, 10, 13)))

    def test_nth_weekday_last_and_missing(self):
        self.assertEqual(nth_weekday(2026, 5, 0, -1), datetime.date(2026, 5, 25))
        with self.assertRaises(ValueError):
            nth_weekday(2026, 2, 0, 5)
        fifth_monday = DoodleSchedule(kind="nth_weekday", month=2, weekday=0, nth=5)
        self.assertEqual(fifth_monday.start_dates(2026), [])

    def test_holiday(self):
        diwali = DoodleSchedule(kind="holiday", country="IN", holiday="diwali")
        self.assertEqual(diwali.start_dates(2026), [datetime.date(2026, 11, 8)])
        self.assertTrue(diwali.occurs_on(datetime.date(2026, 11, 8)))

    def test_holiday_of_another_category(self):
        hanukkah = holiday_dates("IL", "Hanukkah", 2026)
        self.assertEqual(len(hanukkah), 8)
        self.assertEqual(hanukkah[0], "2026-12-05")

    def test_holiday_skips_observed_days(self):
        # July 4, 2026 is a Saturday, so Friday July 3 is "Independence Day (observed)".
        independence_day = holiday_dates("US", "Independence Day", 2026)
        self.assertIn("2026-07-04", independence_day)
        self.assertNotIn("2026-07-03", independence_day)

    def test_holiday_of_an_unsupported_country(self):
        with patch.object(schedule, "logger") as logger:
            self.assertEqual(holiday_dates("ZZ", "Anything", 2026), [])
        logger.warning.assert_called_once()

    def test_never(self):
        never = DoodleSchedule(kind="never")
        self.assertEqual(never.start_dates(2026), [])
        self.assertFalse(never.occurs_on(datetime.date(2026, 1, 1)))

    def test_fields_of_each_kind_are_required(self):
        for fields in [
            {"kind": "fixed", "month": 3},
            {"kind": "nth_weekday", "month": 10, "weekday": 1},
            {"kind": "holiday", "country": "IN"},
            {"kind": "nth_weekday", "month": 10, "weekday": 1, "nth": 0},
            {"kind": "fixed", "month": 3, "day": 14, "color": "red"},
        ]:
            with self.subTest(fields=fields):
                with self.assertRaises(ValidationError):
                    DoodleSchedule.model_validate(fields)
