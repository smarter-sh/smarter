"""
Test the user menu's Change Profile item: :mod:`smarter.apps.account.views.dashboard.user_profiles`.

Also tests how the chosen profile applies to a request, through
:mod:`smarter.apps.account.profile_selection`: UserProfile.get_selected_object(),
UserProfile.get_cached_object(user=...), get_cached_account_for_user() and
get_cached_avatar_url().
"""

from http import HTTPStatus

from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.const import namespace
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.profile_selection import (
    SELECTED_USER_PROFILE_SESSION_KEY,
    selected_user_profile_id,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import (
    get_cached_account_for_user,
    get_cached_avatar_url,
)
from smarter.apps.account.views.dashboard.profile_image import ProfileImageView
from smarter.apps.account.views.dashboard.urls import DashboardNamedUrls
from smarter.lib import json
from smarter.lib.typing import SmarterDictType

OAUTH_IMAGE = "https://example.com/second-account-picture.png"


class TestUserProfiles(TestAccountMixin):
    """A student who is enrolled in two courses: the non-admin user, with a second, newer profile."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.second_account = Account.objects.create(
            name=f"test_account_second_{cls.hash_suffix}",
            company_name=f"TestAccount_Second_{cls.hash_suffix}",
            is_default_account=False,
        )
        cls.second_profile = UserProfile.objects.create(
            user=cls.non_admin_user, account=cls.second_account, is_test=True, profile_image_url=OAUTH_IMAGE
        )

    @classmethod
    def tearDownClass(cls):
        UserProfile.objects.filter(pk=cls.second_profile.pk).delete()
        cls.second_account.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.non_admin_user)
        self.addCleanup(self.client.logout)
        self.url = reverse(f"{namespace}:{DashboardNamedUrls.ACCOUNT_USER_PROFILES}")
        self.select_url = reverse(f"{namespace}:{DashboardNamedUrls.ACCOUNT_USER_PROFILE_SELECT}")

    def select(self, user_profile_id: int | None) -> object:
        """Set the request's chosen profile, as the middleware does, until the test ends."""
        token = selected_user_profile_id.set(user_profile_id)
        self.addCleanup(selected_user_profile_id.reset, token)
        return token

    def post(self, url: str, body: SmarterDictType | None = None, status: int = HTTPStatus.OK) -> SmarterDictType:
        response = self.client.post(url, data=json.dumps(body or {}), content_type="application/json")
        self.assertEqual(response.status_code, status, response.content[:300])
        return json.loads(response.content)

    def test_urls(self):
        """The views are routed under the account dashboard, where the user menu's profile image is."""
        self.assertEqual(self.url, "/account/dashboard/user-profiles/")
        self.assertEqual(self.select_url, "/account/dashboard/user-profiles/select/")

    def test_lists_the_profiles_newest_first_and_the_newest_is_current(self):
        data = self.post(self.url)
        profiles = data["userProfiles"]
        self.assertEqual([p["id"] for p in profiles], [self.second_profile.pk, self.non_admin_user_profile.pk])
        self.assertEqual(
            set(profiles[0]), {"id", "accountNumber", "accountName", "createdAt", "isCurrent"}, profiles[0]
        )
        self.assertEqual(profiles[0]["accountNumber"], self.second_account.account_number)
        self.assertEqual(profiles[0]["accountName"], self.second_account.company_name)
        self.assertTrue(profiles[0]["createdAt"].startswith(str(self.second_profile.created_at.year)))
        self.assertEqual([p["isCurrent"] for p in profiles], [True, False])

    def test_select_makes_the_console_act_as_the_chosen_profile(self):
        """Choosing the older profile lasts for the session: the list, and every console page, act as it."""
        data = self.post(self.select_url, {"userProfileId": self.non_admin_user_profile.pk})
        self.assertEqual([p["isCurrent"] for p in data["userProfiles"]], [False, True])
        self.assertEqual(self.client.session[SELECTED_USER_PROFILE_SESSION_KEY], self.non_admin_user_profile.pk)
        data = self.post(self.url)
        self.assertEqual([p["isCurrent"] for p in data["userProfiles"]], [False, True])
        page = self.client.get("/dashboard/")
        self.assertEqual(page.status_code, HTTPStatus.OK)
        self.assertIn(f'smarter-account-name="{self.account.company_name}"', page.content.decode())

        self.post(self.select_url, {"userProfileId": self.second_profile.pk})
        page = self.client.get("/dashboard/")
        self.assertIn(f'smarter-account-name="{self.second_account.company_name}"', page.content.decode())

    def test_select_refuses_another_users_profile(self):
        data = self.post(self.select_url, {"userProfileId": self.user_profile.pk}, status=HTTPStatus.NOT_FOUND)
        self.assertEqual(data["error"], "Not one of your profiles.")
        self.assertNotIn(SELECTED_USER_PROFILE_SESSION_KEY, self.client.session)

    def test_select_refuses_an_invalid_body(self):
        for body in ({}, {"userProfileId": "twelve"}, {"userProfileId": 1, "other": True}):
            with self.subTest(body=body):
                self.post(self.select_url, body, status=HTTPStatus.BAD_REQUEST)
        response = self.client.post(self.select_url, data="not json", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_anonymous_requests_are_refused(self):
        self.client.logout()
        for url in (self.url, self.select_url):
            with self.subTest(url=url):
                response = self.client.post(url, data="{}", content_type="application/json")
                self.assertNotEqual(response.status_code, HTTPStatus.OK)
                self.assertNotIn(b"userProfiles", response.content)

    def test_resolvers_act_as_the_chosen_profile(self):
        """Get_cached_object(user=...), get_cached_account_for_user() and get_cached_avatar_url() act as the chosen profile."""
        user = self.non_admin_user
        self.assertEqual(UserProfile.get_cached_object(user=user).pk, self.second_profile.pk)
        self.assertEqual(get_cached_avatar_url(user_id=user.pk), OAUTH_IMAGE)

        self.select(self.second_profile.pk)
        self.assertEqual(get_cached_account_for_user(user=user).pk, self.second_account.pk)
        self.assertEqual(get_cached_avatar_url(user_id=user.pk), OAUTH_IMAGE)

        self.select(self.non_admin_user_profile.pk)
        self.assertEqual(UserProfile.get_selected_object(user.pk).pk, self.non_admin_user_profile.pk)
        self.assertEqual(UserProfile.get_cached_object(user=user).pk, self.non_admin_user_profile.pk)
        self.assertEqual(get_cached_account_for_user(user=user).pk, self.account.pk)
        self.assertNotEqual(get_cached_avatar_url(user_id=user.pk), OAUTH_IMAGE)
        # a user and an account name the profile, whatever was chosen.
        self.assertEqual(
            UserProfile.get_cached_object(user=user, account=self.second_account).pk, self.second_profile.pk
        )

    def test_a_choice_of_another_users_profile_is_ignored(self):
        """The chosen id applies only to its own user, e.g. when a request resolves the account's admin."""
        self.select(self.user_profile.pk)
        self.assertIsNone(UserProfile.get_selected_object(self.non_admin_user.pk))
        self.assertEqual(UserProfile.get_cached_object(user=self.non_admin_user).pk, self.second_profile.pk)
        self.assertEqual(UserProfile.get_selected_object(self.admin_user.pk).pk, self.user_profile.pk)

    def test_a_choice_of_a_deleted_profile_is_ignored(self):
        self.select(2**31 - 1)
        self.assertIsNone(UserProfile.get_selected_object(self.non_admin_user.pk))
        self.assertEqual(UserProfile.get_cached_object(user=self.non_admin_user).pk, self.second_profile.pk)

    def test_no_choice(self):
        self.assertIsNone(UserProfile.get_selected_object(self.non_admin_user.pk))
        self.select(self.non_admin_user_profile.pk)
        self.assertIsNone(UserProfile.get_selected_object(None))

    def test_profile_image_belongs_to_the_chosen_profile(self):
        """The user menu uploads the image of the profile that the console acts as."""
        request = RequestFactory().post("/account/dashboard/profile-image/")
        request.user = self.non_admin_user
        view = ProfileImageView()
        self.assertEqual(view.own_user_profile(request).pk, self.second_profile.pk)
        self.select(self.non_admin_user_profile.pk)
        self.assertEqual(view.own_user_profile(request).pk, self.non_admin_user_profile.pk)
