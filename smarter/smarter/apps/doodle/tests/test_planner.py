"""Test :mod:`smarter.apps.doodle.planner`."""

import datetime
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext

from smarter.apps.doodle import planner
from smarter.apps.doodle.const import DEFAULT_THEME_SLUG, PLANNING_DAYS
from smarter.apps.doodle.models import (
    Doodle,
    DoodleArtwork,
    DoodleEditorRun,
    DoodleEditorRunStatus,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)
from smarter.apps.doodle.regions import DoodleRegion

from .mixins import DIWALI, QUIET_DAY, DoodleTestMixin


class TestPlanner(DoodleTestMixin):
    """The planner chooses each region's doodle of each day."""

    def test_candidates_best_first(self):
        christmas_eve = datetime.date(2026, 12, 24)
        slugs = [theme.slug for theme in planner.candidates(christmas_eve, DoodleRegion.US)]
        self.assertEqual(slugs, ["christmas"])

    def test_candidates_of_a_day_read_once(self):
        christmas_eve = datetime.date(2026, 12, 24)
        due = planner.due_on(christmas_eve)
        with CaptureQueriesContext(connection) as queries:
            slugs = [theme.slug for theme in planner.candidates(christmas_eve, DoodleRegion.US, due=due)]
            artworks = [theme.artwork.sha256 for theme in due]
        self.assertEqual(len(queries), 0)
        self.assertEqual(slugs, ["christmas"])
        self.assertTrue(artworks)

    def test_catalog_leaves_out_the_svg_text(self):
        themes = planner.catalog()
        self.assertTrue(themes)
        for theme in themes:
            deferred = theme.get_deferred_fields()
            self.assertIn("props_svg", deferred)
            self.assertIn("svg", theme.artwork.get_deferred_fields())
            self.assertNotEqual(theme.slug, DEFAULT_THEME_SLUG)
        default = planner.default_theme()
        self.assertIn("svg", default.artwork.get_deferred_fields())

    def test_regional_theme_wins_at_equal_priority(self):
        theme = self.theme("christmas")
        local = DoodleTheme(slug="zz-local", priority=theme.priority, regions=["us"])
        everywhere = DoodleTheme(slug="aa-everywhere", priority=theme.priority, regions=["*"])
        ordered = sorted([everywhere, local], key=planner.candidate_order)
        self.assertEqual([t.slug for t in ordered], ["zz-local", "aa-everywhere"])

    def test_plan_a_holiday(self):
        self.addCleanup(self.delete_doodles, DIWALI)
        doodle = planner.plan_doodle(DIWALI, DoodleRegion.SOUTH_ASIA)
        self.assertEqual(doodle.theme.slug, "diwali")
        self.assertEqual(doodle.source, DoodleSource.CALENDAR)
        self.assertEqual(doodle.status, DoodleStatus.APPROVED)
        self.assertEqual(doodle.artwork, doodle.theme.artwork)
        self.assertEqual(doodle.caption, "Happy Diwali!")
        self.assertIn("Diwali is due", doodle.reason)

    def test_a_region_that_the_theme_does_not_apply_to(self):
        self.addCleanup(self.delete_doodles, DIWALI)
        doodle = planner.plan_doodle(DIWALI, DoodleRegion.MX)
        self.assertEqual(doodle.theme.slug, DEFAULT_THEME_SLUG)
        self.assertEqual(doodle.source, DoodleSource.DEFAULT)

    def test_the_default_on_a_quiet_day(self):
        self.addCleanup(self.delete_doodles, QUIET_DAY)
        doodle = planner.plan_doodle(QUIET_DAY, DoodleRegion.GLOBAL)
        self.assertEqual(doodle.theme.slug, DEFAULT_THEME_SLUG)
        self.assertEqual(doodle.reason, "Nothing is due.")

    def test_replanning_updates_the_doodle(self):
        self.addCleanup(self.delete_doodles, DIWALI)
        first = planner.plan_doodle(DIWALI, DoodleRegion.US)
        Doodle.objects.filter(pk=first.pk).update(caption="stale")
        second = planner.plan_doodle(DIWALI, DoodleRegion.US)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.caption, "Happy Diwali!")

    def test_a_doodle_that_a_person_chose_is_kept(self):
        self.addCleanup(self.delete_doodles, DIWALI)
        doodle = planner.plan_doodle(DIWALI, DoodleRegion.EUROPE)
        halloween = self.theme("halloween")
        Doodle.objects.filter(pk=doodle.pk).update(theme=halloween, source=DoodleSource.HUMAN)
        kept = planner.plan_doodle(DIWALI, DoodleRegion.EUROPE)
        self.assertEqual(kept.theme.slug, "halloween")

    def test_a_doodle_that_the_editor_chose_is_kept(self):
        self.addCleanup(self.delete_doodles, DIWALI)
        doodle = planner.plan_doodle(DIWALI, DoodleRegion.OCEANIA)
        default = self.theme(DEFAULT_THEME_SLUG)
        Doodle.objects.filter(pk=doodle.pk).update(theme=default, artwork=default.artwork, source=DoodleSource.LLM)
        kept = planner.plan_doodle(DIWALI, DoodleRegion.OCEANIA)
        self.assertEqual(kept.theme.slug, DEFAULT_THEME_SLUG)

    def test_nothing_to_plan_without_a_catalog(self):
        with patch.object(planner, "default_theme", return_value=None):
            with patch.object(planner, "logger") as logger:
                self.assertIsNone(planner.plan_doodle(QUIET_DAY, DoodleRegion.GLOBAL))
        logger.warning.assert_called_once()

    def test_planning_window(self):
        window = planner.planning_window(days=7, today=datetime.date(2026, 11, 3))
        self.assertEqual(window[0], datetime.date(2026, 11, 2))
        self.assertEqual(window[-1], datetime.date(2026, 11, 10))
        self.assertEqual(len(window), 9)

    def test_planning_window_defaults_to_today(self):
        self.assertEqual(len(planner.planning_window()), PLANNING_DAYS + 2)

    def test_plan_doodles_plans_every_region_of_every_day(self):
        today = DIWALI - datetime.timedelta(days=2)
        window = planner.planning_window(days=2, today=today)
        for day in window:
            self.addCleanup(self.delete_doodles, day)
        # purge() would delete every doodle 30 days before 2035, including the dev platform's.
        with (
            patch.object(planner, "purge", return_value=0) as purge,
            patch.object(planner, "catalog", wraps=planner.catalog) as catalog,
        ):
            planned = planner.plan_doodles(days=2, today=today)
        purge.assert_called_once_with(today=today)
        # the catalog is read once, not once for each day and region.
        catalog.assert_called_once()
        self.assertEqual(planned, len(window) * len(DoodleRegion.values))
        diwali = Doodle.objects.get(date=DIWALI, region=DoodleRegion.SOUTH_ASIA)
        self.assertEqual(diwali.theme.slug, "diwali")

    def test_plan_doodles_without_a_catalog(self):
        with patch.object(planner, "plan_doodle", return_value=None), patch.object(planner, "purge", return_value=0):
            self.assertEqual(planner.plan_doodles(days=1, today=QUIET_DAY), 0)

    def test_purge(self):
        old_day = datetime.date(2001, 1, 1)
        self.addCleanup(self.delete_doodles, old_day)
        planner.plan_doodle(old_day, DoodleRegion.GLOBAL)
        orphan = DoodleArtwork.for_svg(f"<svg>{self.hash_suffix}</svg>")
        drawn_artwork = DoodleArtwork.for_svg(f"<svg>drawn {self.hash_suffix}</svg>")
        drawn = DoodleTheme.objects.create(
            slug=f"ai-test-{self.hash_suffix}",
            name="Drawn",
            category="culture",
            alt_text="Drawn.",
            artwork=drawn_artwork,
            is_active=False,
            is_generated=True,
        )
        old_run = DoodleEditorRun.objects.create(date=old_day, status=DoodleEditorRunStatus.SUCCEEDED)
        deleted = planner.purge(today=datetime.date(2026, 11, 3))
        self.assertGreaterEqual(deleted, 1)
        self.assertFalse(Doodle.objects.filter(date=old_day).exists())
        self.assertFalse(DoodleArtwork.objects.filter(pk=orphan.pk).exists())
        self.assertFalse(DoodleTheme.objects.filter(pk=drawn.pk).exists())
        self.assertFalse(DoodleArtwork.objects.filter(pk=drawn_artwork.pk).exists())
        self.assertFalse(DoodleEditorRun.objects.filter(pk=old_run.pk).exists())
        self.assertTrue(DoodleArtwork.objects.filter(pk=self.theme(DEFAULT_THEME_SLUG).artwork_id).exists())

    def test_purge_defaults_to_today(self):
        self.assertGreaterEqual(planner.purge(), 0)
