"""Tests of smarter.apps.api.web.session.views: GET /api/web/session/."""

from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory
from waffle.testutils import override_switch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.web.session import views
from smarter.apps.api.web.session.contract import ConsoleSession
from smarter.apps.api.web.urls import ApiWebReverseNames
from smarter.apps.dashboard.context_processors import sidebar_context
from smarter.apps.dashboard.views.views.api.welcome import WELCOME_SHOWN_SESSION_KEY
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches


class TestConsoleSessionView(TestAccountMixin):
    """Test the session api for a visitor, a user and a superuser."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse(ApiWebReverseNames.namespace, ApiWebReverseNames.console_session_view)

    def tearDown(self):
        self.client.logout()
        super().tearDown()

    def get_session(self) -> ConsoleSession:
        """GET the session api, and validate its JSON against the contract."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return ConsoleSession.model_validate(response.json())

    def test_url(self):
        """The api is at /api/web/session/."""
        self.assertEqual(self.url, "/api/web/session/")

    def test_anonymous(self):
        """A visitor gets what the sign-in pages need, and nothing about any user."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        session = ConsoleSession.model_validate(response.json())
        self.assertFalse(session.is_authenticated)
        self.assertIsNone(session.user)
        self.assertIsNone(session.account)
        self.assertIsNone(session.onboarding)
        self.assertIsNone(session.welcome)
        self.assertIsNone(session.badges)
        self.assertIsNone(session.sidebar)
        self.assertFalse(session.flags.terminal)
        self.assertEqual(session.cookies.csrf_cookie_name, settings.CSRF_COOKIE_NAME)
        self.assertTrue(session.branding.product_name)
        self.assertGreaterEqual(len(session.language.languages), 1)

    def test_sets_the_csrf_cookie_and_is_never_cached(self):
        """The first call gives the console a CSRF token for its first POST, and is never cached."""
        response = self.client.get(self.url)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertIn("no-cache", response["Cache-Control"])

    def test_only_get(self):
        """The api is read-only."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_sign_up_follows_its_switch(self):
        """Sign_in.sign_up reports the ENABLE_ACCOUNT_REGISTRATION switch."""
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=True):
            self.assertTrue(self.get_session().sign_in.sign_up)
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=False):
            self.assertFalse(self.get_session().sign_in.sign_up)

    def test_oauth_providers(self):
        """Sign_in.google and sign_in.github come from the shared OAuth checks."""
        with (
            mock.patch.object(views, "google_oauth_enabled", return_value=True),
            mock.patch.object(views, "github_oauth_enabled", return_value=False),
        ):
            session = self.get_session()
        self.assertTrue(session.sign_in.google)
        self.assertFalse(session.sign_in.github)

    def test_signed_in_user(self):
        """A user gets who they are, their account, and their welcome and onboarding state."""
        self.client.force_login(self.non_admin_user)
        session = self.get_session()
        self.assertTrue(session.is_authenticated)
        self.assertIsNotNone(session.user)
        self.assertEqual(session.user.username, self.non_admin_user.username)  # type: ignore[union-attr]
        self.assertFalse(session.user.is_superuser)  # type: ignore[union-attr]
        self.assertGreaterEqual(session.user.user_profile_count, 1)  # type: ignore[union-attr]
        self.assertIsNotNone(session.account)
        self.assertEqual(session.account.account_number, self.account.account_number)  # type: ignore[union-attr]
        self.assertIsNotNone(session.onboarding)
        self.assertIsNotNone(session.welcome)
        self.assertEqual(session.badges.extension_updates, 0)  # type: ignore[union-attr]
        self.assertFalse(session.flags.terminal)

    def test_superuser_terminal_and_badges(self):
        """The terminal is on only for a superuser, and only a superuser's badges are counted."""
        self.client.force_login(self.admin_user)
        with (
            mock.patch.object(views, "terminal_enabled", return_value=True),
            mock.patch.object(views, "update_count", return_value=3),
        ):
            session = self.get_session()
        self.assertTrue(session.flags.terminal)
        self.assertEqual(session.badges.extension_updates, 3)  # type: ignore[union-attr]

        self.client.force_login(self.non_admin_user)
        with (
            mock.patch.object(views, "terminal_enabled", return_value=True),
            mock.patch.object(views, "update_count", return_value=3) as update_count,
        ):
            session = self.get_session()
        self.assertFalse(session.flags.terminal)
        self.assertEqual(session.badges.extension_updates, 0)  # type: ignore[union-attr]
        update_count.assert_not_called()

    def test_sidebar(self):
        """A user's sidebar has the server-rendered sidebar's urls, without a superuser's or staff's items."""
        self.client.force_login(self.non_admin_user)
        session = self.get_session()
        links = sidebar_context()["sidebar"]
        sidebar = session.sidebar
        self.assertIsNotNone(sidebar)
        self.assertEqual(sidebar.dashboard, links["dashboard"])  # type: ignore[union-attr]
        self.assertEqual(sidebar.secrets, links["secrets"])  # type: ignore[union-attr]
        self.assertEqual(sidebar.api_keys, links["api_keys"])  # type: ignore[union-attr]
        self.assertIsNone(sidebar.terminal)  # type: ignore[union-attr]
        self.assertIsNone(sidebar.infrastructure_resources)  # type: ignore[union-attr]
        self.assertIsNone(sidebar.admin)  # type: ignore[union-attr]

    def test_sidebar_of_a_superuser_and_of_a_staff_user(self):
        """A superuser gets the terminal, while it is on, and the infrastructure; staff get the admin."""
        links = {
            **sidebar_context()["sidebar"],
            "terminal": "/dashboard/terminal/",
            "prompt_passthrough": "/dashboard/passthrough/",
        }
        superuser = mock.Mock(is_superuser=True, is_staff=False)
        console_flags = views.flags(None).model_copy(update={"terminal": True, "passthrough": False})
        with mock.patch.object(views, "sidebar_context", return_value={"sidebar": links}):
            sidebar = views.sidebar(superuser, console_flags)
            staff = views.sidebar(mock.Mock(is_superuser=False, is_staff=True), console_flags)
        self.assertEqual(sidebar.terminal, "/dashboard/terminal/")
        self.assertEqual(sidebar.infrastructure_resources, links["infrastructure_resources"])
        self.assertIsNone(sidebar.admin)
        self.assertIsNone(sidebar.prompt_passthrough)
        self.assertEqual(staff.admin, links["admin"])
        self.assertIsNone(staff.infrastructure_resources)

    def test_welcome_shows_once_per_session(self):
        """The welcome dialog opens by itself until it is closed in this session."""
        request = RequestFactory().get(self.url)
        request.user = self.non_admin_user
        request.session = {}
        with mock.patch.object(views, "user_was_welcomed", return_value=False):
            first = views.welcome(request, self.non_admin_user)
            request.session = {WELCOME_SHOWN_SESSION_KEY: True}
            later = views.welcome(request, self.non_admin_user)
        self.assertTrue(first.show)
        self.assertTrue(first.show_at_startup)
        self.assertFalse(later.show)
        self.assertTrue(later.show_at_startup)

    def test_unresolved_user_is_anonymous(self):
        """A user whom get_resolved_user() can't resolve gets the visitor's session, not an error."""
        request = RequestFactory().get(self.url)
        request.user = AnonymousUser()
        session = views.console_session(request)
        self.assertFalse(session.is_authenticated)

    def test_user_without_a_profile(self):
        """A user with no profile has no account, and the default avatar."""
        self.client.force_login(self.non_admin_user)
        with mock.patch.object(views.UserProfile, "get_cached_object", side_effect=views.UserProfile.DoesNotExist):
            session = self.get_session()
        self.assertIsNone(session.account)
        self.assertTrue(session.user.profile_image_url)  # type: ignore[union-attr]

    def test_missing_marketing_site_url(self):
        """A platform without a marketing site gets empty links, not the text None."""
        # smarter_settings is frozen, so patch in a copy without a marketing site.
        settings_without_site = views.smarter_settings.model_copy(update={"marketing_site_url": None})
        with mock.patch.object(views, "smarter_settings", settings_without_site):
            branding = views.branding()
        self.assertEqual(branding.marketing_site_url, "")
        self.assertEqual(branding.legal_url, "")
