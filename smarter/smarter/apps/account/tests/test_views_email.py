"""Test the welcome email's dev preview view, in each language."""

from django.test import RequestFactory
from django.utils import translation

from smarter.apps.account.views.email import EmailWelcomeView

from .mixins import TestAccountMixin


class TestEmailWelcomeView(TestAccountMixin):
    """Test that the preview renders in the request's language, or in its language parameter."""

    def get(self, query: str = "", language: str = "en"):
        request = RequestFactory().get(f"/dashboard/account/email/welcome/jane/{query}")
        request.user = self.admin_user
        with translation.override(language):
            return EmailWelcomeView.as_view()(request, first_name="jane")

    def test_request_language(self):
        response = self.get(language="fr")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bonjour Jane,", response.content.decode())

    def test_language_parameter(self):
        response = self.get("?language=pt-br", language="es")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Olá, Jane,", response.content.decode())

    def test_english(self):
        response = self.get()
        self.assertIn("Howdy Jane,", response.content.decode())

    def test_unknown_language(self):
        self.assertEqual(self.get("?language=xx").status_code, 400)
