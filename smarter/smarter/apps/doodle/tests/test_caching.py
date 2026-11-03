"""Test :mod:`smarter.apps.doodle.caching`, the cached reads of the doodle api."""

from unittest.mock import patch

from smarter.apps.doodle import caching
from smarter.apps.doodle.caching import artwork_svg, artwork_url, doodle_of_the_day
from smarter.apps.doodle.const import DEFAULT_THEME_SLUG
from smarter.apps.doodle.models import DoodleStatus
from smarter.apps.doodle.planner import plan_doodle
from smarter.apps.doodle.regions import DoodleRegion

from .mixins import DIWALI, QUIET_DAY, DoodleTestMixin


class TestDoodleCaching(DoodleTestMixin):
    """The doodle of a day falls back to the global doodle, then to the default theme."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        plan_doodle(DIWALI, DoodleRegion.GLOBAL)

    def test_artwork_url(self):
        self.assertTrue(artwork_url("a" * 64).startswith("/api/v1/doodles/artwork/aaaa"))

    def test_fallbacks(self):
        day = QUIET_DAY.isoformat()
        doodle_of_the_day.invalidate(day, DoodleRegion.OCEANIA)
        with patch.object(caching, "logger"):
            doodle = doodle_of_the_day(day, DoodleRegion.OCEANIA)
        self.assertEqual(doodle.theme, DEFAULT_THEME_SLUG)
        self.assertRegex(doodle.image_url, r"^/api/v1/doodles/artwork/")

        doodle_of_the_day.invalidate(day, DoodleRegion.OCEANIA)
        with patch.object(caching, "default_theme", return_value=None), patch.object(caching, "logger") as logger:
            doodle = doodle_of_the_day(day, DoodleRegion.OCEANIA)
        logger.warning.assert_called_once()
        self.assertEqual(doodle.image_url, "/static/doodle/base.svg")
        doodle_of_the_day.invalidate(day, DoodleRegion.OCEANIA)

    def test_a_region_without_an_approved_doodle_falls_back_to_the_global_one(self):
        day = DIWALI.isoformat()
        doodle = plan_doodle(DIWALI, DoodleRegion.SOUTH_ASIA)
        doodle.status = DoodleStatus.PROPOSED
        doodle.save()
        self.addCleanup(plan_doodle, DIWALI, DoodleRegion.SOUTH_ASIA)
        doodle_of_the_day.invalidate(day, DoodleRegion.SOUTH_ASIA)
        result = doodle_of_the_day(day, DoodleRegion.SOUTH_ASIA)
        self.assertEqual(result.theme, "diwali")
        self.assertEqual(result.region, DoodleRegion.SOUTH_ASIA)

    def test_artwork_svg_is_cached(self):
        theme = self.theme("christmas")
        self.assertEqual(artwork_svg(theme.artwork.sha256), theme.artwork.svg)
