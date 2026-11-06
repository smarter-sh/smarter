"""Tests of smarter.lib.django.i18n: the languages that the web console offers."""

from django.conf import settings
from django.test import override_settings

from smarter.lib.django.i18n import console_languages
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestConsoleLanguages(SmarterTestBase):
    """Test the language list of the console's language menu."""

    def test_every_language_in_its_own_name(self):
        """Each language of settings.LANGUAGES is listed once, in order, named in itself with a capital."""
        languages = console_languages()
        self.assertEqual(len(languages), len(settings.LANGUAGES))
        for code, name in languages:
            with self.subTest(code=code):
                self.assertEqual(name[:1], name[:1].upper())

    @override_settings(LANGUAGES=[("en", "English"), ("es", "Spanish")])
    def test_local_names(self):
        """Spanish is listed as Español."""
        self.assertEqual(console_languages(), [("en", "English"), ("es", "Español")])
