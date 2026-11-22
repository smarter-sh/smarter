"""Test the welcome dialog's api views, :mod:`smarter.apps.dashboard.views.views.api.welcome`, and its state in the session."""

from http import HTTPStatus
from unittest import mock

from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.web.session.contract import ConsoleSession, ConsoleWelcome
from smarter.apps.api.web.urls import ApiWebReverseNames
from smarter.apps.dashboard.views.views.api import welcome
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.llmclient.models import LLMClient
from smarter.lib import json
from smarter.lib.typing import SmarterDictType


class TestWelcomeApiViews(TestAccountMixin):
    """Test WelcomeView and WelcomeDismissView, and the welcome dialog's state in the console's session."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(f"{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.welcome}")
        self.dismiss_url = reverse(f"{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.welcome_dismiss}")
        self.addCleanup(self.forget_welcome)
        self.forget_welcome()

    def forget_welcome(self):
        """Make the non-admin user a user who has never closed the welcome dialog."""
        UserProfile.objects.filter(user=self.non_admin_user).update(welcomed_at=None, show_welcome_at_startup=False)
        welcome.user_was_welcomed.invalidate(self.non_admin_user.pk)
        welcome.user_shows_welcome_at_startup.invalidate(self.non_admin_user.pk)

    def post(self, url: str, body: SmarterDictType | None = None) -> SmarterDictType:
        self.client.force_login(self.non_admin_user)
        if body is None:
            response = self.client.post(url)
        else:
            response = self.client.post(url, data=json.dumps(body), content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        return json.loads(response.content)

    def test_welcome(self):
        """Test that a new user hasn't been welcomed, and gets the links of the last step."""
        data = self.post(self.url)
        self.assertFalse(data["welcomed"])
        self.assertEqual(set(data["urls"]), {"weather", "llmclients", "docs", "project"})
        self.assertTrue(data["urls"]["llmclients"].startswith("/"))
        self.assertTrue(data["urls"]["docs"].startswith("https://"))
        self.assertTrue(data["urls"]["project"].startswith("https://"))

    def test_weather_llmclient_is_the_users_own(self):
        """Test that the Get Weather link is the Prompt Workbench chat of the user's own copy, when they have one."""
        llmclient = LLMClient.objects.create(
            name=welcome.WEATHER_LLMCLIENT_NAME, user_profile=self.non_admin_user_profile
        )
        self.addCleanup(llmclient.delete)
        url = self.post(self.url)["urls"]["weather"]
        self.assertTrue(url.startswith("/"), url)
        self.assertTrue(url.endswith(f"/llm-clients/{llmclient.hashed_id}/prompt/"), url)

    def test_without_a_weather_llmclient(self):
        """Test that there is no Get Weather link when the user can't read a Get Weather LLMClient."""
        with mock.patch.object(welcome, "WEATHER_LLMCLIENT_NAME", f"no-such-llmclient-{self.hash_suffix}"):
            self.assertIsNone(self.post(self.url)["urls"]["weather"])

    def test_dismiss(self):
        """Test that dismissing records the date once, and that the user is welcomed from then on."""
        self.assertFalse(welcome.user_was_welcomed(self.non_admin_user.pk))
        self.assertTrue(self.post(self.dismiss_url)["welcomed"])
        welcomed_at = UserProfile.objects.get(pk=self.non_admin_user_profile.pk).welcomed_at
        self.assertIsNotNone(welcomed_at)
        self.assertTrue(welcome.user_was_welcomed(self.non_admin_user.pk))
        self.assertTrue(self.post(self.url)["welcomed"])
        # a second dismiss keeps the date of the first.
        self.post(self.dismiss_url)
        self.assertEqual(UserProfile.objects.get(pk=self.non_admin_user_profile.pk).welcomed_at, welcomed_at)

    def test_dismiss_show_at_startup(self):
        """Test that dismissing records the date either way, and the Show at startup box's choice."""
        self.assertTrue(self.post(self.dismiss_url, {"showAtStartup": True})["welcomed"])
        profile = UserProfile.objects.get(pk=self.non_admin_user_profile.pk)
        self.assertIsNotNone(profile.welcomed_at)
        self.assertTrue(profile.show_welcome_at_startup)
        self.assertTrue(welcome.user_shows_welcome_at_startup(self.non_admin_user.pk))
        self.assertTrue(welcome.welcome_opens_at_sign_in(self.non_admin_user.pk))
        self.assertTrue(self.post(self.dismiss_url, {"showAtStartup": False})["welcomed"])
        profile = UserProfile.objects.get(pk=self.non_admin_user_profile.pk)
        self.assertIsNotNone(profile.welcomed_at)
        self.assertFalse(profile.show_welcome_at_startup)
        self.assertFalse(welcome.user_shows_welcome_at_startup(self.non_admin_user.pk))
        self.assertFalse(welcome.welcome_opens_at_sign_in(self.non_admin_user.pk))

    def test_a_new_user_sees_the_dialog_until_they_close_it(self):
        """Test that the dialog opens by itself for a new user, whose Show at startup box is unticked."""
        self.assertTrue(welcome.welcome_opens_at_sign_in(self.non_admin_user.pk))
        self.assertFalse(welcome.user_shows_welcome_at_startup(self.non_admin_user.pk))

    def test_dismiss_invalid_body(self):
        """Test that a body that isn't a WelcomeDismissRequest is refused, and records nothing."""
        self.client.force_login(self.non_admin_user)
        for body in ("not json", "[]", '{"showAtStartup": "maybe"}', '{"other": true}'):
            with self.subTest(body=body):
                response = self.client.post(self.dismiss_url, data=body, content_type="application/json")
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIsNone(UserProfile.objects.get(pk=self.non_admin_user_profile.pk).welcomed_at)

    def test_anonymous(self):
        for url in (self.url, self.dismiss_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, HTTPStatus.FOUND)

    def test_unresolved_user(self):
        """Test that a user whom get_resolved_user() can't resolve is refused, rather than an error."""
        with mock.patch.object(welcome, "get_resolved_user", return_value=None):
            for url in (self.url, self.dismiss_url):
                with self.subTest(url=url):
                    self.client.force_login(self.non_admin_user)
                    self.assertEqual(self.client.post(url).status_code, HTTPStatus.UNAUTHORIZED)

    def session_welcome(self) -> ConsoleWelcome:
        """The welcome dialog's state in the console's session, which the console's frame reads."""
        response = self.client.get(reverse(f"{ApiWebReverseNames.namespace}:{ApiWebReverseNames.console_session_view}"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        welcome_state = ConsoleSession.model_validate(response.json()).welcome
        self.assertIsNotNone(welcome_state)
        return welcome_state  # type: ignore[return-value]

    def test_the_console_opens_the_dialog_until_it_is_closed(self):
        """Test that the console opens the dialog for a new user, and doesn't once they have closed it."""
        self.client.force_login(self.non_admin_user)
        state = self.session_welcome()
        self.assertTrue(state.show)
        self.assertFalse(state.show_at_startup)
        self.post(self.dismiss_url)
        state = self.session_welcome()
        self.assertFalse(state.show)
        self.assertFalse(state.show_at_startup)

    def test_closing_it_keeps_it_closed_at_the_next_sign_in(self):
        """Test that a user who closed the dialog, with its box as it came, doesn't see it at the next sign-in."""
        self.client.force_login(self.non_admin_user)
        state = self.session_welcome()
        self.assertTrue(state.show)
        # the console posts the box as it came: unticked.
        self.post(self.dismiss_url, {"showAtStartup": state.show_at_startup})
        # signing in again starts a new session.
        self.client.logout()
        self.client.force_login(self.non_admin_user)
        self.assertFalse(self.session_welcome().show)

    def test_shows_once_per_session_at_startup(self):
        """Test that, with Show at startup ticked, the dialog opens by itself once per session, i.e. per sign-in."""
        self.client.force_login(self.non_admin_user)
        self.post(self.dismiss_url, {"showAtStartup": True})
        state = self.session_welcome()
        self.assertFalse(state.show)
        self.assertTrue(state.show_at_startup)
        # signing in again starts a new session.
        self.client.logout()
        self.client.force_login(self.non_admin_user)
        self.assertTrue(self.session_welcome().show)
