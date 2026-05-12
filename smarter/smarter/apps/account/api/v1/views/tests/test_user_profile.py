# pylint: disable=wrong-import-position
"""Test UserProfileView for API end point."""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from smarter.apps.account.api.v1.urls import AccountAPINamespaces
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.api.v1.const import namespace as api_v1_namespace
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)

User = get_user_model()


class TestUserProfileView(TestAccountMixin):
    """Test UserProfileView API end point."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_profile_view]
        )
        self.url = reverse(self.reverse_name, args=[self.user_profile.id])  # type: ignore

    def test_get_superuser_success(self):
        """Superuser can GET user profile by id."""
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_get_non_superuser_forbidden(self):
        """Non-superuser cannot GET user profile by id."""
        self.admin_user.is_superuser = False
        self.admin_user.save()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN])

    def test_get_invalid_id(self):
        """GET with invalid id returns 404."""
        url = reverse(self.reverse_name, args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_not_allowed(self):
        """POST is not allowed."""
        response = self.client.post(self.url, data={})
        self.assertIn(response.status_code, [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN])

    def test_patch_not_allowed(self):
        """PATCH is not allowed."""
        response = self.client.patch(self.url, data={})
        self.assertIn(response.status_code, [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN])


class TestUserProfileViewDeleteNonSuperuser(TestAccountMixin):
    """Test UserProfileView API end point."""

    def setUp(self):
        super().setUp()
        self.admin_user.is_superuser = False
        self.admin_user.save()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_profile_view]
        )
        self.url = reverse(self.reverse_name, args=[self.user_profile.id])  # type: ignore

    def test_delete_non_superuser_forbidden(self):
        """Non-superuser cannot DELETE user profile by id."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


class TestUserProfileViewDeleteInvalidID(TestAccountMixin):
    """Test UserProfileView API end point."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_profile_view]
        )
        self.url = reverse(self.reverse_name, args=[self.user_profile.id])  # type: ignore

    def test_delete_invalid_id(self):
        """DELETE with invalid id returns 403 or 404."""
        url = reverse(self.reverse_name, args=[999999])
        response = self.client.delete(url)
        # Depending on logic, could be 403 or 404
        self.assertIn(response.status_code, [HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND])


class TestUserProfileViewDeleteInternalError(TestAccountMixin):
    """Test UserProfileView API end point."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_profile_view]
        )
        self.url = reverse(self.reverse_name, args=[self.non_admin_user_profile.id])  # type: ignore

    def test_delete_internal_error(self):
        """DELETE handles internal error gracefully."""
        # Simulate error by deleting user_profile before delete
        self.non_admin_user_profile.delete()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class TestUserProfileViewDeleteSuperuserSuccess(TestAccountMixin):
    """Test UserProfileView API end point."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_profile_view]
        )
        self.url = reverse(self.reverse_name, args=[self.user_profile.id])  # type: ignore

    def test_delete_superuser_success(self):
        """Superuser can DELETE user profile by id."""
        response = self.client.delete(self.url)
        self.assertIn(response.status_code, [HTTPStatus.FOUND, HTTPStatus.SEE_OTHER])
        # Should redirect after delete
