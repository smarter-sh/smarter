"""Test the web console's cookie notice, templates/common/cookie-notice.html."""

from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse
from django.utils import translation

from smarter.lib.unittest.base_classes import SmarterTestBase

TEMPLATE = "common/cookie-notice.html"


class TestCookieNotice(SmarterTestBase):
    """Test the cookie notice that every page of the web console shows until it is closed."""

    def test_renders_the_notice_hidden_until_its_script_shows_it(self):
        """The notice starts hidden, so a visitor who closed it before never sees it flash."""
        html = render_to_string(TEMPLATE, {"branding": {"smarter_project_website_url": "https://example.com"}})
        self.assertIn('id="smarter-cookie-notice"', html)
        self.assertIn("hidden>", html)
        self.assertIn("We use cookies to improve your experience.", html)
        self.assertIn("data-smarter-cookie-notice-close", html)
        self.assertIn("smarter-cookie-notice-dismissed", html)

    def test_links_to_the_privacy_policy_of_the_project_website(self):
        """The privacy link goes to the Smarter Project website's privacy page."""
        html = render_to_string(TEMPLATE, {"branding": {"smarter_project_website_url": "https://example.com"}})
        self.assertIn('href="https://example.com/privacy"', html)

    def test_links_to_smarter_sh_without_branding(self):
        """Pages rendered without the branding context, such as error pages, still link somewhere."""
        html = render_to_string(TEMPLATE, {})
        self.assertIn('href="https://smarter.sh/privacy"', html)

    def test_its_explanation_is_not_sent_to_the_browser(self):
        """The template's comment stays on the server."""
        self.assertNotIn("<!--", render_to_string(TEMPLATE, {}))

    def test_is_translated(self):
        """The notice renders in the active language."""
        with translation.override("es"):
            html = render_to_string(TEMPLATE, {})
        self.assertIn("Usamos cookies para mejorar tu experiencia.", html)
        self.assertIn("Política de privacidad", html)
        self.assertIn("Cerrar", html)

    def test_every_page_has_the_notice(self):
        """Base.html includes the notice, e.g. on the login page."""
        response = Client().get(reverse("login_view"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="smarter-cookie-notice"', response.content.decode())
