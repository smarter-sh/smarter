"""Test :mod:`smarter.apps.doodle.caching`, the cached reads of the doodle api."""

from unittest.mock import patch

from smarter.apps.doodle import caching
from smarter.apps.doodle.caching import artwork_svg, artwork_url, doodle_of_the_day
from smarter.apps.doodle.const import DEFAULT_THEME_SLUG
from smarter.apps.doodle.models import Doodle, DoodleSource, DoodleStatus
from smarter.apps.doodle.planner import plan_doodle
from smarter.apps.doodle.regions import DoodleRegion

from .mixins import DIWALI, QUIET_DAY, DoodleTestMixin


class TestDoodleCaching(DoodleTestMixin):
    """The doodle of a day falls back to the calendar's choice, then to the default theme, then to the base scene."""

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

    def test_a_region_without_an_approved_doodle_gets_the_calendars_choice(self):
        day = DIWALI.isoformat()
        doodle = plan_doodle(DIWALI, DoodleRegion.SOUTH_ASIA)
        assert doodle is not None
        default = self.theme(DEFAULT_THEME_SLUG)
        Doodle.objects.filter(pk=doodle.pk).update(
            theme=default, artwork=default.artwork, source=DoodleSource.LLM, status=DoodleStatus.PROPOSED
        )
        self.addCleanup(Doodle.objects.filter(pk=doodle.pk).delete)
        doodle_of_the_day.invalidate(day, DoodleRegion.SOUTH_ASIA)
        result = doodle_of_the_day(day, DoodleRegion.SOUTH_ASIA)
        self.assertEqual(result.theme, "diwali")
        self.assertFalse(result.is_default)
        self.assertEqual(result.ai_credit, "")
        self.assertEqual(result.region, DoodleRegion.SOUTH_ASIA)
        doodle_of_the_day.invalidate(day, DoodleRegion.SOUTH_ASIA)

    def test_the_credit_of_a_doodle_that_the_editor_chose(self):
        day = DIWALI.isoformat()
        doodle = plan_doodle(DIWALI, DoodleRegion.EUROPE)
        assert doodle is not None
        Doodle.objects.filter(pk=doodle.pk).update(source=DoodleSource.LLM)
        self.addCleanup(Doodle.objects.filter(pk=doodle.pk).delete)
        doodle_of_the_day.invalidate(day, DoodleRegion.EUROPE)
        result = doodle_of_the_day(day, DoodleRegion.EUROPE)
        self.assertEqual(result.ai_credit, "chosen")
        doodle_of_the_day.invalidate(day, DoodleRegion.EUROPE)

    def test_the_default_that_the_editor_chose_is_the_default(self):
        day = QUIET_DAY.isoformat()
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.MX)
        assert doodle is not None
        Doodle.objects.filter(pk=doodle.pk).update(source=DoodleSource.LLM)
        self.addCleanup(Doodle.objects.filter(pk=doodle.pk).delete)
        doodle_of_the_day.invalidate(day, DoodleRegion.MX)
        result = doodle_of_the_day(day, DoodleRegion.MX)
        self.assertTrue(result.is_default)
        self.assertEqual(result.ai_credit, "")
        doodle_of_the_day.invalidate(day, DoodleRegion.MX)

    def test_artwork_svg_is_cached(self):
        theme = self.theme("christmas")
        self.assertEqual(artwork_svg(theme.artwork.sha256), theme.artwork.svg)
