"""Test :mod:`smarter.apps.docs.views.webserver`: robots.txt and sitemap.xml."""

import tempfile
from http import HTTPStatus
from pathlib import Path

from defusedxml import ElementTree
from django.test import Client, override_settings
from waffle.testutils import override_switch

from smarter.apps.dashboard.views.console_app import CONSOLE_INDEX_PATH
from smarter.apps.docs.views.webserver import absolute_url, sitemap_pages
from smarter.common.conf import smarter_settings
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest.base_classes import SmarterTestBase

SITEMAP_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class TestSitemapXml(SmarterTestBase):
    """Test that sitemap.xml lists exactly the public pages, and that robots.txt points to it."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def sitemap_locs(self) -> list[str]:
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        root = ElementTree.fromstring(response.content)
        return [loc.text or "" for loc in root.findall("sm:url/sm:loc", SITEMAP_NAMESPACE)]

    def test_lists_every_public_page_once(self):
        locs = self.sitemap_locs()
        self.assertEqual(len(locs), len(sitemap_pages()))
        self.assertEqual(len(locs), len(set(locs)))
        for loc in locs:
            self.assertTrue(loc.startswith(smarter_settings.environment_url.rstrip("/") + "/"), loc)

    def test_every_page_is_public(self):
        """
        Every listed page answers an anonymous GET with 200: no 404s, redirects or login pages.

        The sign-up page is the single-page console's, so the test gives it a built console.
        """
        base = smarter_settings.environment_url.rstrip("/")
        static_root = tempfile.TemporaryDirectory()
        self.addCleanup(static_root.cleanup)
        index_path = Path(static_root.name) / CONSOLE_INDEX_PATH
        index_path.parent.mkdir(parents=True)
        index_path.write_text("<!doctype html><title>console</title>", encoding="utf-8")
        built = override_settings(STATIC_ROOT=static_root.name)
        built.enable()
        self.addCleanup(built.disable)
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=True):
            locs = self.sitemap_locs()
        for loc in locs:
            with self.subTest(loc=loc):
                response = self.client.get(loc.removeprefix(base))
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_lists_the_sign_up_page_only_while_registration_is_open(self):
        """The sign-up page answers 404 while registration is switched off, so the sitemap leaves it out."""
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=True):
            open_paths = [page_path for page_path, _ in sitemap_pages()]
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=False):
            closed_paths = [page_path for page_path, _ in sitemap_pages()]
        self.assertIn("/register/", open_paths)
        self.assertNotIn("/register/", closed_paths)

    def test_robots_txt_points_to_the_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn(f"Sitemap: {absolute_url('/sitemap.xml')}", response.content.decode())
