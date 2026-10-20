"""Test the welcome dialog's api views, :mod:`smarter.apps.dashboard.views.views.api.welcome`, and its template tags."""

from http import HTTPStatus
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.templatetags.react_welcome import welcome_dialog
from smarter.apps.dashboard.views.views.api import welcome
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.llmclient.models import LLMClient
from smarter.lib import json
from smarter.lib.typing import SmarterDictType

from ..const import namespace


class TestWelcomeApiViews(TestAccountMixin):
    """Test WelcomeView and WelcomeDismissView, and the welcome dialog's root element on console pages."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.welcome}")
        self.dismiss_url = reverse(
            f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.welcome_dismiss}"
        )
        self.addCleanup(self.forget_welcome)
        self.forget_welcome()

    def forget_welcome(self):
        """Make the non-admin user a user who has never closed the welcome dialog."""
        UserProfile.objects.filter(user=self.non_admin_user).update(welcomed_at=None)
        welcome.user_was_welcomed.invalidate(self.non_admin_user.id)

    def post(self, url: str) -> SmarterDictType:
        self.client.force_login(self.non_admin_user)
        response = self.client.post(url)
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
        self.assertFalse(welcome.user_was_welcomed(self.non_admin_user.id))
        self.assertTrue(self.post(self.dismiss_url)["welcomed"])
        welcomed_at = UserProfile.objects.get(pk=self.non_admin_user_profile.pk).welcomed_at
        self.assertIsNotNone(welcomed_at)
        self.assertTrue(welcome.user_was_welcomed(self.non_admin_user.id))
        self.assertTrue(self.post(self.url)["welcomed"])
        # a second dismiss keeps the date of the first.
        self.post(self.dismiss_url)
        self.assertEqual(UserProfile.objects.get(pk=self.non_admin_user_profile.pk).welcomed_at, welcomed_at)

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

    def test_welcome_dialog_tag(self):
        """Test the root element's attributes, for a new user, and for a request without a signed-in user."""
        request = RequestFactory().get("/dashboard/")
        request.user = self.non_admin_user
        attributes = welcome_dialog({"request": request})
        self.assertTrue(attributes["show"])
        self.assertEqual(attributes["first_name"], self.non_admin_user.first_name or "")
        self.assertEqual(attributes["dismiss_api_url"], self.dismiss_url)
        request.user = AnonymousUser()
        attributes = welcome_dialog({"request": request})
        self.assertFalse(attributes["show"])
        self.assertEqual(attributes["first_name"], "")

    def test_console_pages_mount_the_dialog(self):
        """Test that a console page opens the dialog for a new user, and doesn't once they have closed it."""
        self.client.force_login(self.non_admin_user)
        page = self.client.get("/dashboard/")
        self.assertEqual(page.status_code, HTTPStatus.OK)
        content = page.content.decode()
        self.assertIn('id="smarter-welcome-root"', content)
        self.assertIn('smarter-welcome-show="true"', content)
        self.assertIn(f'smarter-welcome-dismiss-api-url="{self.dismiss_url}"', content)
        self.assertIn("data-smarter-welcome-open", content)
        self.post(self.dismiss_url)
        self.assertIn('smarter-welcome-show="false"', self.client.get("/dashboard/").content.decode())
