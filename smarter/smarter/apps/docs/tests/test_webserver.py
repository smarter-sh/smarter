"""Test :mod:`smarter.apps.docs.views.webserver`: robots.txt and sitemap.xml."""

from http import HTTPStatus

from defusedxml import ElementTree
from django.test import Client

from smarter.apps.docs.views.webserver import absolute_url, sitemap_pages
from smarter.common.conf import smarter_settings
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
        """Every listed page answers an anonymous GET with 200: no 404s, redirects or login pages."""
        base = smarter_settings.environment_url.rstrip("/")
        for loc in self.sitemap_locs():
            with self.subTest(loc=loc):
                response = self.client.get(loc.removeprefix(base))
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_robots_txt_points_to_the_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn(f"Sitemap: {absolute_url('/sitemap.xml')}", response.content.decode())
