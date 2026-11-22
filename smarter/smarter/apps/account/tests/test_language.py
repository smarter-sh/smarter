"""Test :mod:`smarter.apps.account.language` and SmarterLocaleMiddleware, which remember a user's language."""

from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import translation

from smarter.apps.account.language import (
    chosen_console_language,
    console_language_code,
    remember_console_language,
)
from smarter.apps.account.middleware import SmarterLocaleMiddleware
from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin


class TestConsoleLanguage(TestAccountMixin):
    """The language menu's choice is kept in the user's profiles, and restored where the cookie is missing."""

    def setUp(self):
        super().setUp()
        self.addCleanup(self.forget_language)
        self.forget_language()
        self.addCleanup(translation.deactivate)

    def forget_language(self):
        """Make the non-admin user a user who has never chosen a language."""
        UserProfile.objects.filter(user=self.non_admin_user).update(
            console_language="", language=settings.LANGUAGE_CODE
        )

    def profile(self) -> UserProfile:
        return UserProfile.objects.get(pk=self.non_admin_user_profile.pk)

    def test_the_language_cookie_lasts_a_year(self):
        """The cookie outlives the browser's session, rather than Django's default of a session cookie."""
        self.assertEqual(settings.LANGUAGE_COOKIE_AGE, 60 * 60 * 24 * 365)

    def test_console_language_code(self):
        """A code is matched to one of the console's languages, or is empty."""
        self.assertEqual(console_language_code("es"), "es")
        self.assertEqual(console_language_code("es-MX"), "es")
        self.assertEqual(console_language_code("pt-BR"), "pt-br")
        self.assertEqual(console_language_code("xx"), "")
        self.assertEqual(console_language_code(""), "")
        self.assertEqual(console_language_code(None), "")

    def test_set_language_remembers_a_signed_in_users_choice(self):
        """The language menu's post sets the cookie, and stores the choice in the user's profiles."""
        client = Client()
        client.force_login(self.non_admin_user)
        response = client.post(reverse("set_language"), {"language": "fr", "next": "/dashboard/"})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        cookie = response.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertEqual(cookie.value, "fr")
        self.assertEqual(cookie["max-age"], settings.LANGUAGE_COOKIE_AGE)
        profile = self.profile()
        self.assertEqual(profile.console_language, "fr")
        self.assertEqual(profile.language, "fr")
        self.assertEqual(chosen_console_language(self.non_admin_user.pk), "fr")

    def test_set_language_ignores_an_unsupported_language(self):
        """A language that the console doesn't offer isn't stored."""
        client = Client()
        client.force_login(self.non_admin_user)
        client.post(reverse("set_language"), {"language": "xx", "next": "/dashboard/"})
        self.assertEqual(self.profile().console_language, "")

    def test_set_language_by_get_changes_nothing(self):
        """Django's view only redirects a GET, so nothing is stored."""
        client = Client()
        client.force_login(self.non_admin_user)
        client.get(reverse("set_language"), {"language": "fr", "next": "/dashboard/"})
        self.assertEqual(self.profile().console_language, "")

    def test_set_language_for_a_visitor(self):
        """A visitor gets the cookie, and no profile changes."""
        response = Client().post(reverse("set_language"), {"language": "es", "next": "/"})
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "es")
        self.assertEqual(self.profile().console_language, "")

    def test_a_signed_in_user_without_the_cookie_gets_their_language(self):
        """A page load without the cookie, e.g. on another device, is in the user's language, and sets the cookie."""
        remember_console_language(self.non_admin_user.pk, "es")
        client = Client(headers={"accept-language": "fr"})
        client.force_login(self.non_admin_user)
        response = client.get(reverse("set_language"))
        self.assertEqual(response.headers["Content-Language"], "es")
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "es")
        # the next request has the cookie, so it isn't set again.
        response = client.get(reverse("set_language"))
        self.assertEqual(response.headers["Content-Language"], "es")
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)

    def middleware_response(self, request) -> HttpResponse:
        middleware = SmarterLocaleMiddleware(lambda request: HttpResponse("ok"))
        return middleware(request)  # type: ignore[return-value]

    def test_the_cookie_wins_over_the_profile(self):
        """The browser's cookie is the choice on this device: the profile isn't read."""
        remember_console_language(self.non_admin_user.pk, "es")
        request = RequestFactory().get("/dashboard/")
        request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = "fr"
        request.user = self.non_admin_user
        response = self.middleware_response(request)
        self.assertEqual(response.headers["Content-Language"], "fr")
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)

    def test_the_browsers_language_without_a_choice(self):
        """A user who never chose a language gets the browser's, and no cookie."""
        request = RequestFactory().get("/dashboard/", headers={"accept-language": "fr"})
        request.user = self.non_admin_user
        response = self.middleware_response(request)
        self.assertEqual(response.headers["Content-Language"], "fr")
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)

    def test_visitors_and_api_keys_get_the_browsers_language(self):
        """A visitor, or a request with an api key, isn't given a profile's language."""
        remember_console_language(self.non_admin_user.pk, "es")
        visitor = RequestFactory().get("/", headers={"accept-language": "fr"})
        visitor.user = AnonymousUser()
        api_request = RequestFactory().get("/", headers={"accept-language": "fr", "authorization": "Token abc"})
        api_request.user = self.non_admin_user
        for request in (visitor, api_request):
            with self.subTest(user=str(request.user)):
                response = self.middleware_response(request)
                self.assertEqual(response.headers["Content-Language"], "fr")
                self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)
