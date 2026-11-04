"""Test :mod:`smarter.apps.doodle.themes`, the theme catalog."""

import os

import yaml
from pydantic import ValidationError

from smarter.apps.doodle.const import (
    DEFAULT_THEME_SLUG,
    PROPS_PLACEHOLDER_ID,
    THEMES_PATH,
)
from smarter.apps.doodle.models import DoodleTheme
from smarter.apps.doodle.regions import DoodleRegion
from smarter.apps.doodle.themes import (
    DoodleThemeSpec,
    load_themes,
    read_theme,
    theme_files,
)
from smarter.common.exceptions import SmarterValueError

from .mixins import DoodleTestMixin

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class TestThemes(DoodleTestMixin):
    """The catalog is valid, and loads into the database."""

    def test_every_theme_of_the_catalog_loads(self):
        files = theme_files()
        self.assertEqual(len(self.themes), len(files))
        slugs = [theme.slug for theme in self.themes]
        self.assertIn(DEFAULT_THEME_SLUG, slugs)
        for theme in self.themes:
            with self.subTest(theme=theme.slug):
                self.assertTrue(theme.is_active)
                self.assertIn(f'id="{PROPS_PLACEHOLDER_ID}"', theme.artwork.svg)
                self.assertIn(f"<title>{theme.alt_text}</title>", theme.artwork.svg.replace("&#x27;", "'"))

    def test_the_catalog_has_no_unused_props(self):
        used = set()
        for path in theme_files():
            spec, _ = read_theme(path)
            used.add(spec.props or f"{spec.slug}.svg")
        svgs = {name for name in os.listdir(THEMES_PATH) if name.endswith(".svg")}
        self.assertEqual(svgs - used, set())

    def test_every_region_has_a_theme_of_its_own_or_of_all_regions(self):
        for region in DoodleRegion.values:
            with self.subTest(region=region):
                found = [theme for theme in self.themes if region in theme.regions or "*" in theme.regions]
                self.assertGreater(len(found), 1)

    def test_props_are_shared(self):
        us = self.theme("thanksgiving-us")
        ca = self.theme("thanksgiving-ca")
        self.assertEqual(us.props_svg, ca.props_svg)

    def test_loading_again_changes_nothing(self):
        before = {theme.slug: theme.artwork_id for theme in self.themes}
        again = load_themes()
        after = {theme.slug: theme.artwork_id for theme in again}
        self.assertEqual(before, after)

    def test_a_removed_theme_is_deactivated(self):
        folder = os.path.join(DATA, "valid")
        load_themes(folder)
        self.addCleanup(load_themes)
        active = set(DoodleTheme.objects.filter(is_active=True).values_list("slug", flat=True))
        self.assertEqual(active, {"test-sunny-day", "test-cloudy-day"})
        self.assertFalse(self.theme(DEFAULT_THEME_SLUG).is_active)

    def test_a_theme_without_props_is_the_base_scene(self):
        spec, props_svg = read_theme(os.path.join(DATA, "valid", "test-cloudy-day.yaml"))
        self.assertEqual(props_svg, "")
        self.assertEqual(spec.caption, "")

    def test_invalid_catalogs_change_nothing(self):
        cases = {
            "invalid-region": ValidationError,
            "wrong-slug": ValueError,
            "missing-props": ValueError,
            "bad-props": SmarterValueError,
        }
        count = DoodleTheme.objects.count()
        for folder, error in cases.items():
            with self.subTest(folder=folder):
                with self.assertRaises(error):
                    load_themes(os.path.join(DATA, folder))
                self.assertEqual(DoodleTheme.objects.count(), count)
                self.assertTrue(self.theme(DEFAULT_THEME_SLUG).is_active)

    def test_the_link_must_be_https(self):
        with open(os.path.join(DATA, "insecure-link.yaml"), encoding="utf-8") as file:
            data = yaml.safe_load(file)
        with self.assertRaises(ValidationError):
            DoodleThemeSpec.model_validate(data)
