"""Tests for the smarter_email template tags."""

from unittest.mock import patch

from django.template import Context, Template

from smarter.apps.dashboard.templatetags.smarter_email import absolute_static
from smarter.common.conf import smarter_settings
from smarter.lib.unittest.base_classes import SmarterTestBase

LOGO = "images/logo/smarter-crop.png"
MODULE = "smarter.apps.dashboard.templatetags.smarter_email"


class TestAbsoluteStatic(SmarterTestBase):
    """Test the absolute_static template tag."""

    def test_relative_static_url_is_joined_to_the_platform_url(self):
        """While the server serves the static files, the url is the platform's."""
        with patch(f"{MODULE}.static", return_value=f"/static/{LOGO}"):
            url = absolute_static(LOGO)
        self.assertEqual(url, smarter_settings.environment_url.rstrip("/") + f"/static/{LOGO}")
        self.assertTrue(url.startswith("http"))

    def test_cdn_static_url_is_returned_unchanged(self):
        """While the static files are on the CDN, the url is the CDN's, not glued onto the platform's."""
        cdn = f"https://cdn.platform.example.com/static/{LOGO}"
        with patch(f"{MODULE}.static", return_value=cdn):
            self.assertEqual(absolute_static(LOGO), cdn)

    def test_template_renders_an_absolute_url(self):
        """The tag loads and renders from a template."""
        html = Template("{% load smarter_email %}{% absolute_static '" + LOGO + "' %}").render(Context())
        self.assertTrue(html.startswith("http"))
        self.assertTrue(html.endswith(LOGO))
        self.assertEqual(html.count("://"), 1)


class TestSmarterLogoUrl(SmarterTestBase):
    """Test the smarter_logo_url template tag."""

    def test_logo_url_is_on_the_project_cdn(self):
        """The logo's url is the project CDN's url plus the logo's path."""
        html = Template("{% load smarter_email %}{% smarter_logo_url %}").render(Context())
        self.assertEqual(html, f"{smarter_settings.smarter_project_cdn_url.rstrip('/')}/{LOGO}")
