"""Test :mod:`smarter.apps.dashboard.templatetags.react_dashboard_user_menu`, the user menu at the top right of the console."""

import re
from html import unescape
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.cache import SessionStore
from django.templatetags.static import static
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.models.user_profile import DEFAULT_PROFILE_IMAGE
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.templatetags import react_dashboard_user_menu
from smarter.apps.dashboard.templatetags.react_dashboard_user_menu import (
    dashboard_user_menu,
    languages_json,
)
from smarter.lib import json
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets

MANAGER = "smarter.apps.dashboard.templatetags.react_dashboard_user_menu.templatetag_manager"
ASSETS = ReactAppAssets(css=["assets/index.css"], js=["assets/index.js"])


class TestReactDashboardUserMenu(TestAccountMixin):
    """Test the template tags, and the menu's root element on a console page."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)

    def attributes(self, user, path: str = "/dashboard/?tab=1") -> dict:
        request = RequestFactory().get(path)
        request.user = user
        request.session = SessionStore()
        return dashboard_user_menu({"request": request})

    def test_registered(self):
        self.assertIn("dashboard_user_menu_react_assets", react_dashboard_user_menu.register.tags)
        self.assertIn("dashboard_user_menu", react_dashboard_user_menu.register.tags)

    def test_react_assets(self):
        with patch(f"{MANAGER}.reactapp_build_assets", ASSETS):
            self.assertEqual(react_dashboard_user_menu.dashboard_user_menu_react_assets(), ASSETS)

    def test_signed_in_user(self):
        attributes = self.attributes(self.non_admin_user)
        self.assertEqual(attributes["root_id"], "smarter-dashboard-user-menu-root")
        self.assertTrue(attributes["is_authenticated"])
        self.assertEqual(attributes["username"], self.non_admin_user.username)
        self.assertEqual(attributes["email"], self.non_admin_user.email)
        self.assertEqual(attributes["first_name"], self.non_admin_user.first_name)
        self.assertEqual(attributes["last_name"], self.non_admin_user.last_name)
        self.assertFalse(attributes["is_superuser"])
        self.assertFalse(attributes["is_staff"])
        self.assertEqual(attributes["user_profile_count"], 1)
        self.assertEqual(attributes["account_number"], self.account.account_number)
        self.assertEqual(attributes["account_name"], self.account.company_name)
        self.assertEqual(attributes["next_url"], "/dashboard/?tab=1")
        self.assertEqual(attributes["set_language_url"], reverse("set_language"))
        self.assertEqual(attributes["profile_image_api_url"], "/account/dashboard/profile-image/")
        self.assertEqual(attributes["user_profiles_api_url"], "/account/dashboard/user-profiles/")
        self.assertEqual(attributes["user_profile_select_api_url"], "/account/dashboard/user-profiles/select/")
        self.assertEqual(attributes["logout_url"], "/logout/")
        self.assertEqual(attributes["current_language"], "en")
        self.assertEqual(len(attributes["smarter_request_id"]), 32)

    def test_superuser(self):
        attributes = self.attributes(self.admin_user)
        self.assertTrue(attributes["is_superuser"])

    def test_counts_every_profile(self):
        """A user with a second profile, e.g. in a second course, gets the Change Profile item."""
        account = Account.objects.create(
            name=f"test_account_menu_{self.hash_suffix}", company_name=f"TestAccount_Menu_{self.hash_suffix}"
        )
        self.addCleanup(account.delete)
        profile = UserProfile.objects.create(user=self.non_admin_user, account=account, is_test=True)
        self.addCleanup(UserProfile.get_cached_object, invalidate=True, user=self.non_admin_user)
        self.addCleanup(UserProfile.objects.filter(pk=profile.pk).delete)
        # the user's one profile is cached, from an earlier test.
        UserProfile.get_cached_object(invalidate=True, user=self.non_admin_user)
        attributes = self.attributes(self.non_admin_user)
        self.assertEqual(attributes["user_profile_count"], 2)
        # the newest profile, unless the user chooses another.
        self.assertEqual(attributes["account_name"], account.company_name)

    def test_anonymous_request(self):
        attributes = self.attributes(AnonymousUser())
        self.assertFalse(attributes["is_authenticated"])
        self.assertEqual(attributes["username"], "")
        self.assertEqual(attributes["email"], "")
        self.assertEqual(attributes["user_profile_count"], 0)
        self.assertEqual(attributes["account_name"], "")
        self.assertEqual(attributes["profile_image_url"], static(DEFAULT_PROFILE_IMAGE))
        self.assertTrue(attributes["login_url"])

    def test_user_without_a_profile(self):
        with patch.object(UserProfile, "get_cached_object", side_effect=UserProfile.DoesNotExist):
            attributes = self.attributes(self.non_admin_user)
        self.assertTrue(attributes["is_authenticated"])
        self.assertEqual(attributes["account_name"], "")
        self.assertEqual(attributes["profile_image_url"], static(DEFAULT_PROFILE_IMAGE))

    def test_languages_in_their_own_names(self):
        """The Language item lists each language in its own name, capitalized, with the code that set_language takes."""
        with override_settings(LANGUAGES=[("en", "English"), ("es", "Spanish"), ("pt-br", "Brazilian Portuguese")]):
            languages = json.loads(languages_json())
        self.assertEqual(
            languages,
            [
                {"code": "en", "name": "English"},
                {"code": "es", "name": "Español"},
                {"code": "pt-br", "name": "Português Brasileiro"},
            ],
        )

    def test_one_language(self):
        """With only English, the React app hides the Language item."""
        with override_settings(LANGUAGES=[("en", "English")]):
            self.assertEqual(json.loads(languages_json()), [{"code": "en", "name": "English"}])

    def test_console_pages_mount_the_menu(self):
        self.client.force_login(self.non_admin_user)
        with patch(f"{MANAGER}.reactapp_build_assets", ASSETS):
            response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode()
        self.assertIn('id="smarter-dashboard-user-menu-root"', content)
        self.assertIn('smarter-is-authenticated="true"', content)
        self.assertIn(f'smarter-email="{self.non_admin_user.email}"', content)
        self.assertIn('src="/static/react/%40smarter/dashboard-user-menu/assets/index.js"', content)
        self.assertIn("/static/react/%40smarter/dashboard-user-menu/assets/index.css", content)
        # the html minifier may quote the attribute with single quotes.
        match = re.search(r"smarter-languages=([\"'])(.*?)\1", content, re.DOTALL)
        self.assertIsNotNone(match)
        languages = json.loads(unescape(match.group(2)))
        self.assertIn({"code": "es", "name": "Español"}, languages)
