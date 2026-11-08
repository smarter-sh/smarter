"""Test that every HTML email renders as something a mail client can show."""

import re

from django.template.loader import render_to_string

from smarter.apps.account.models import contact_email_context, welcome_email_context
from smarter.lib.unittest.base_classes import SmarterTestBase

TEMPLATES = (
    "account/email/data-export.html",
    "account/email/slack-invitation.html",
    "account/email/welcome.html",
    "account/authentication/email/account-activation.html",
    "account/authentication/email/password-reset.html",
)
LINK = "https://platform.example.com/link/"


class TestEmailTemplates(SmarterTestBase):
    """Each email uses the shared layout: no scripts, styles or svgs, and absolute image urls."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        context = welcome_email_context(first_name="jane")
        context.update(contact_email_context(first_name="jane", email="jane@example.com"))
        context["data_export"] = {"url": LINK, "manifest_count": 2, "failed_count": 0, "size": "1.0 KB", "hours": 24}
        context["password_reset"] = {"url": LINK}
        context["account_activation"] = {"url": LINK}
        cls.rendered = {template: render_to_string(template, context) for template in TEMPLATES}

    def test_no_scripts_styles_or_stylesheets(self):
        """Mail clients strip these, so the layout must not depend on them."""
        for template, html in self.rendered.items():
            with self.subTest(template=template):
                self.assertNotIn("<script", html)
                self.assertNotIn("<style", html)
                self.assertNotIn('rel="stylesheet"', html)

    def test_images_are_absolute_pngs(self):
        """A mail client has no page url to resolve a relative src against, and Gmail blocks svgs."""
        for template, html in self.rendered.items():
            with self.subTest(template=template):
                sources = re.findall(r'<img[^>]*\ssrc="([^"]*)"', html)
                self.assertTrue(sources)
                for src in sources:
                    self.assertRegex(src, r"^https?://[^/]+/")
                    self.assertEqual(src.count("://"), 1, src)
                    self.assertFalse(src.endswith(".svg"), src)

    def test_logo_is_on_the_project_cdn(self):
        """Every email shows the same logo."""
        for template, html in self.rendered.items():
            with self.subTest(template=template):
                self.assertIn("/images/logo/smarter-crop.png", html)

    def test_links_reach_the_email(self):
        """The email's own link is in it."""
        for template in TEMPLATES[:1] + TEMPLATES[3:]:
            with self.subTest(template=template):
                self.assertIn(LINK, self.rendered[template])
