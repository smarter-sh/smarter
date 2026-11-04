"""Test :mod:`smarter.apps.doodle.regions`."""

import datetime
import unittest

from smarter.apps.doodle.regions import (
    ZONE_COUNTRIES,
    DoodleRegion,
    country_for_timezone,
    local_date,
    region_countries,
    region_for_timezone,
    theme_applies_to,
    valid_timezone,
)


class TestRegions(unittest.TestCase):
    """A browser's time zone gives the visitor's region and local date."""

    def test_zone_countries_are_read_from_tzdata(self):
        self.assertGreater(len(ZONE_COUNTRIES), 300)
        self.assertEqual(ZONE_COUNTRIES["America/Vancouver"], "CA")

    def test_country_for_timezone(self):
        self.assertEqual(country_for_timezone("Asia/Kolkata"), "IN")
        self.assertIsNone(country_for_timezone("UTC"))
        self.assertIsNone(country_for_timezone(None))

    def test_regions_of_countries(self):
        cases = {
            "America/New_York": DoodleRegion.US,
            "Pacific/Honolulu": DoodleRegion.US,
            "America/Toronto": DoodleRegion.CA,
            "America/Mexico_City": DoodleRegion.MX,
            "America/Sao_Paulo": DoodleRegion.LATAM,
            "America/Bogota": DoodleRegion.LATAM,
            "Europe/Paris": DoodleRegion.EUROPE,
            "Africa/Nairobi": DoodleRegion.AFRICA,
            "Asia/Riyadh": DoodleRegion.MIDDLE_EAST,
            "Europe/Istanbul": DoodleRegion.MIDDLE_EAST,
            "Asia/Kolkata": DoodleRegion.SOUTH_ASIA,
            "Asia/Tokyo": DoodleRegion.EAST_ASIA,
            "Asia/Jakarta": DoodleRegion.SOUTHEAST_ASIA,
            "Australia/Sydney": DoodleRegion.OCEANIA,
            "Pacific/Fiji": DoodleRegion.OCEANIA,
        }
        for tz, region in cases.items():
            with self.subTest(tz=tz):
                self.assertEqual(region_for_timezone(tz), region)

    def test_global_when_no_region_applies(self):
        for tz in ["UTC", "Asia/Almaty", "", None, "Not/AZone", "x" * 100, "../../etc/passwd"]:
            with self.subTest(tz=tz):
                self.assertEqual(region_for_timezone(tz), DoodleRegion.GLOBAL)

    def test_valid_timezone(self):
        self.assertIsNotNone(valid_timezone("Europe/Paris"))
        self.assertIsNone(valid_timezone("Europe/Atlantis"))
        self.assertIsNone(valid_timezone(None))

    def test_local_date(self):
        moment = datetime.datetime(2026, 11, 8, 20, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(local_date("Asia/Kolkata", now=moment), datetime.date(2026, 11, 9))
        self.assertEqual(local_date("America/Vancouver", now=moment), datetime.date(2026, 11, 8))
        self.assertEqual(local_date("Not/AZone", now=moment), datetime.date(2026, 11, 8))

    def test_local_date_defaults_to_now(self):
        self.assertIsInstance(local_date("UTC"), datetime.date)

    def test_region_countries(self):
        self.assertEqual(region_countries("ca"), ["CA"])
        self.assertIn("IN", region_countries("south-asia"))
        self.assertIn("BR", region_countries("latam"))
        self.assertNotIn("US", region_countries("latam"))
        self.assertIn("FR", region_countries("europe"))
        self.assertEqual(region_countries("global"), [])

    def test_theme_applies_to(self):
        self.assertTrue(theme_applies_to(["*"], "mx"))
        self.assertTrue(theme_applies_to(["mx", "latam"], "mx"))
        self.assertFalse(theme_applies_to(["us"], "mx"))
