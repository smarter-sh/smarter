"""Test the web console's internationalization: settings, urls, templates and message catalogs."""

from pathlib import Path

from django.conf import settings
from django.template import engines
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils import translation

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.templatetags.smarter_i18n import to_locale
from smarter.lib.unittest.base_classes import SmarterTestBase

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"


class TestI18nSettings(SmarterTestBase):
    """Test the internationalization settings."""

    def test_english_is_the_default_language(self):
        """English is the source language, and the default."""
        self.assertEqual(settings.LANGUAGE_CODE, "en")
        self.assertIn("en", [code for code, _ in settings.LANGUAGES])
        self.assertTrue(settings.USE_I18N)

    def test_locale_middleware_order(self):
        """LocaleMiddleware comes after SessionMiddleware and before CommonMiddleware."""
        middleware = list(settings.MIDDLEWARE)
        locale = middleware.index("django.middleware.locale.LocaleMiddleware")
        self.assertLess(middleware.index("django.contrib.sessions.middleware.SessionMiddleware"), locale)
        self.assertLess(locale, middleware.index("django.middleware.common.CommonMiddleware"))

    def test_i18n_context_processor(self):
        """Templates get LANGUAGES, LANGUAGE_CODE and LANGUAGE_BIDI."""
        processors = settings.TEMPLATES[0]["OPTIONS"]["context_processors"]
        self.assertIn("django.template.context_processors.i18n", processors)

    def test_message_catalogs_exist(self):
        """Each language has a django.po and a djangojs.po in LOCALE_PATHS."""
        locale_dir = Path(settings.LOCALE_PATHS[0])
        for code, _ in settings.LANGUAGES:
            for domain in ("django", "djangojs"):
                po = locale_dir / code / "LC_MESSAGES" / f"{domain}.po"
                self.assertTrue(po.is_file(), f"{po} is missing: run make i18n-messages")


class TestI18nTemplates(SmarterTestBase):
    """Test that the web console's templates compile, and mark their text for translation."""

    def test_every_template_compiles(self):
        """Every template compiles, so none uses {% translate %} without {% load i18n %}."""
        engine = engines["django"]
        templates = sorted(TEMPLATES_DIR.rglob("*.html"))
        self.assertTrue(templates)
        for path in templates:
            with self.subTest(template=str(path.relative_to(TEMPLATES_DIR))):
                engine.from_string(path.read_text(encoding="utf-8"))

    def test_templates_render_in_the_active_language(self):
        """A translated template renders the active language's text, and English by default."""
        engine = engines["django"]
        template = engine.from_string('{% load i18n %}{% translate "Sign In" %}')
        self.assertEqual(template.render({}), "Sign In")
        with translation.override("en"):
            self.assertEqual(template.render({}), "Sign In")


class TestI18nViews(TestAccountMixin):
    """Test the internationalization urls, and the pages that use them."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()

    def tearDown(self):
        """Tear down test fixtures."""
        self.client = None
        return super().tearDown()

    def test_javascript_catalog(self):
        """The JavaScript catalog defines gettext() and friends for the browser."""
        response = self.client.get(reverse("javascript-catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response["Content-Type"])
        content = response.content.decode()
        self.assertIn("django.gettext", content)
        self.assertIn("django.interpolate", content)

    def test_set_language(self):
        """Choosing a language sets the language cookie and returns to the page."""
        response = self.client.post(reverse("set_language"), {"language": "en", "next": "/dashboard/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/dashboard/")
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")

    def test_unsupported_language_falls_back_to_english(self):
        """A browser that asks for a language that isn't available gets English."""
        response = self.client.get(reverse("login_view"), headers={"accept-language": "xx"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('<html lang="en"', content)
        self.assertEqual(response.headers.get("Content-Language"), "en")

    def test_pages_load_the_javascript_catalog(self):
        """Pages load the JavaScript catalog before their own scripts."""
        response = self.client.get(reverse("login_view"))
        content = response.content.decode()
        catalog = content.index(reverse("javascript-catalog"))
        self.assertLess(catalog, content.index("sign-in.js"))

    def test_dashboard_loads_the_javascript_catalog(self):
        """The dashboard pages, which host the React apps, load the JavaScript catalog."""
        self.client.force_login(self.non_admin_user)
        response = self.client.get("/dashboard/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse("javascript-catalog"), response.content.decode())
        self.client.logout()


class TestLanguageMenu(SmarterTestBase):
    """Test the language menu in the user menu of the dashboard's navbar."""

    template = "dashboard/navbar/user-menu-item.html"

    def render(self) -> str:
        """Render the user menu for an anonymous request."""
        request = RequestFactory().get("/dashboard/?tab=1")
        return render_to_string(self.template, {}, request=request)

    def test_hidden_with_one_language(self):
        """With only English, there is nothing to choose, so there is no language menu."""
        with override_settings(LANGUAGES=[("en", "English")]):
            self.assertNotIn('name="language"', self.render())

    def test_lists_every_language_in_its_own_name(self):
        """With more than one language, the menu lists each one, and posts the choice to set_language."""
        with override_settings(LANGUAGES=[("en", "English"), ("es", "Spanish")]):
            html = self.render()
        self.assertIn(f'action="{reverse("set_language")}"', html)
        self.assertIn('value="/dashboard/?tab=1"', html)
        self.assertIn('value="en"', html)
        self.assertIn('value="es"', html)
        self.assertIn("English", html)
        self.assertIn("Español", html)


class TestToLocaleFilter(SmarterTestBase):
    """Test the to_locale template filter."""

    def test_to_locale(self):
        """Language codes become locale names."""
        self.assertEqual(to_locale("en"), "en")
        self.assertEqual(to_locale("en-us"), "en_US")
        self.assertEqual(to_locale("pt-br"), "pt_BR")
        self.assertEqual(to_locale(""), "")

    def test_renders_og_locale(self):
        """Base.html renders the active language's locale as og:locale."""
        html = render_to_string("base.html", {}, request=RequestFactory().get("/"))
        self.assertIn('<meta property="og:locale" content="en" />', html)
