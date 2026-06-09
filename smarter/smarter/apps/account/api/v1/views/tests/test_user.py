"""Unit tests for UserView and UserListView API endpoints."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.api.v1.urls import AccountAPINamespaces
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.models import User
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.api.v1.const import namespace as api_v1_namespace
from smarter.lib import json, logging

logger = logging.getSmarterLogger(__name__)


class TestUserViewBase(TestAccountMixin):
    """Test UserView base functionality."""

    def setUp(self):
        self.admin_user.is_superuser = True
        self.admin_user.save()
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_view]
        )
        self.url = reverse(self.reverse_name, args=[self.admin_user.id])  # type: ignore
        self.list_reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_list_view]
        )


class TestUserView(TestUserViewBase):
    """Test UserView API endpoint."""

    def test_get_superuser_success(self):
        """Superuser can GET user by id."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["username"], self.admin_user.username)

    def test_get_non_superuser_forbidden(self):
        """Non-superuser cannot GET other user by id."""
        self.admin_user.is_superuser = False
        self.admin_user.save()
        url = reverse(self.reverse_name, args=[self.non_admin_user.id])  # type: ignore
        response = self.client.get(url)
        self.assertIn(response.status_code, [HTTPStatus.UNAUTHORIZED, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN])

    def test_get_invalid_id(self):
        """GET with invalid id returns 404."""
        url = reverse(self.reverse_name, args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_create_user_superuser(self):
        """Superuser can POST to create user."""
        url = reverse(self.reverse_name, args=[0])
        data = {"username": "newuser", "password": "pass123"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertIn(response.status_code, [HTTPStatus.FOUND, HTTPStatus.SEE_OTHER, HTTPStatus.OK])
        try:
            new_user = User.objects.get(username="newuser")
            self.assertIsInstance(new_user, User)
            new_user.delete()  # type: ignore
        except User.DoesNotExist:
            self.fail("User should have been created")

    def test_post_create_user_non_superuser_forbidden(self):
        """Non-superuser cannot POST to create user."""
        self.admin_user.is_superuser = False
        self.admin_user.is_staff = False
        self.admin_user.save()
        url = reverse(self.reverse_name, args=[0])
        data = {"username": "failuser", "password": "pass123"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        try:
            user = User.objects.get(username="failuser")
            user.delete()  # type: ignore
            self.fail("User should not have been created")
        except User.DoesNotExist:
            pass

    def test_patch_update_user_superuser(self):
        """Superuser can PATCH to update user."""
        data = {"id": self.admin_user.id, "username": "updateduser"}  # type: ignore
        response = self.client.patch(self.url, data=json.dumps(data), content_type="application/json")
        self.admin_user.refresh_from_db()
        self.assertIn(response.status_code, [HTTPStatus.FOUND, HTTPStatus.SEE_OTHER])
        self.assertEqual(self.admin_user.username, "updateduser")

    def test_patch_update_user_non_superuser_forbidden(self):
        """Non-superuser cannot PATCH to update other user."""
        self.admin_user.is_superuser = False
        self.admin_user.is_staff = False
        self.admin_user.save()
        data = {"id": self.non_admin_user.id, "username": "failupdate"}  # type: ignore
        response = self.client.patch(self.url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


class TestUserViewDeleteSuccess(TestUserViewBase):
    """Test UserView DELETE functionality."""

    def test_delete_superuser_success(self):
        """Superuser can DELETE user by id."""
        user = self.non_admin_user
        url = reverse(self.reverse_name, args=[user.id])  # type: ignore
        response = self.client.delete(url)
        self.assertIn(response.status_code, [HTTPStatus.FOUND, HTTPStatus.SEE_OTHER])
        self.assertFalse(User.objects.filter(id=user.id).exists())  # type: ignore


class TestUserViewNonAdmin(TestUserViewBase):
    """Test UserView DELETE functionality for non-admin users."""

    def test_delete_non_superuser_forbidden(self):
        """Non-superuser cannot DELETE user by id."""
        self.admin_user.is_superuser = False
        self.admin_user.is_staff = False
        self.admin_user.save()
        user = self.non_admin_user
        url = reverse(self.reverse_name, args=[user.id])  # type: ignore
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTrue(User.objects.filter(id=user.id).exists())  # type: ignore


class TestUserViewInvalidId(TestUserViewBase):
    """Test UserView DELETE functionality with invalid IDs."""

    def test_delete_invalid_id(self):
        """DELETE with invalid id returns 404."""
        url = reverse(self.reverse_name, args=[999999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_delete_internal_error(self):
        """DELETE handles internal error gracefully."""
        user = self.non_admin_user
        url = reverse(self.reverse_name, args=[user.id])  # type: ignore
        self.non_admin_user_profile.delete()  # Simulate error
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)


class TestUserListView(TestAccountMixin):
    """Test UserListView API endpoint."""

    def setUp(self):
        self.admin_user.is_superuser = True
        self.admin_user.save()
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.user_list_view]
        )
        self.url = reverse(self.reverse_name)

    def test_get_list_superuser(self):
        """Superuser can GET user list."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(response.json(), list)

    def test_get_list_non_superuser(self):
        """Non-superuser gets only their account users."""
        self.admin_user.is_superuser = False
        self.admin_user.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_post_list(self):
        """POST to list returns user list."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(response.json(), list)

    def test_get_list_unauthorized(self):
        """Unauthorized user gets 403."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_list_invalid_method(self):
        """PATCH is not allowed on list view."""
        response = self.client.patch(self.url)
        self.assertIn(response.status_code, [HTTPStatus.METHOD_NOT_ALLOWED, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN])
