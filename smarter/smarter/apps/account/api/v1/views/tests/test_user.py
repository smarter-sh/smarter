"""Unit tests for UserView and UserListView API endpoints."""

from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.api.v1.urls import AccountAPINamespaces
from smarter.apps.account.api.v1.views import user as user_views
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.models import Account, User, UserProfile
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
        """Unauthenticated user gets 401 or 403."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))

    def test_get_list_invalid_method(self):
        """PATCH is not allowed on list view."""
        response = self.client.patch(self.url)
        self.assertIn(response.status_code, [HTTPStatus.METHOD_NOT_ALLOWED, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN])


class TestUserViewFunctions(TestAccountMixin):
    """Test the user view helper functions directly, for the branches the endpoints rarely reach."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def request(self, user, body="{}", method="post"):
        if method == "get":
            request = self.factory.get("/api/v1/account/users/")
        else:
            request = getattr(self.factory, method)(
                "/api/v1/account/users/", data=body, content_type="application/json"
            )
        request.user = user
        return request

    def create_user(self, prefix: str, account=None, **kwargs) -> User:
        """A throwaway user, with a UserProfile in ``account`` when one is given."""
        user = User.objects.create_user(username=f"{prefix}_{self.hash_suffix}", password="pw", **kwargs)
        self.addCleanup(user.delete)
        if account:
            UserProfile.objects.create(name=user.username, user=user, account=account)
        return user

    def other_account(self) -> Account:
        account = Account.objects.create(name=f"test_user_views_{self.hash_suffix}", company_name="Other")
        self.addCleanup(account.delete)
        return account

    def test_validate_request_body(self):
        for body in ("not json", "[1]", json.dumps({"password": "pw"}), json.dumps({"username": "u"})):
            with self.subTest(body=body):
                response = user_views.validate_request_body(self.request(self.admin_user, body))
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        body = json.dumps({"username": "u", "password": "pw"})
        self.assertIsNone(user_views.validate_request_body(self.request(self.admin_user, body)))

    def test_eval_permissions(self):
        """Test who may modify whom: nobody anonymous, staff within their account, mortals only themselves."""
        mortal = self.create_user("mortal", account=self.account)
        response = user_views.eval_permissions(self.request(AnonymousUser()), mortal)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        homeless = self.create_user("homeless")
        response = user_views.eval_permissions(self.request(homeless), mortal)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        stranger = self.create_user("stranger", account=self.other_account())
        stranger_profile = UserProfile.objects.get(user=stranger)
        response = user_views.eval_permissions(self.request(self.non_admin_user), stranger, stranger_profile)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        mortal_profile = UserProfile.objects.get(user=mortal)
        response = user_views.eval_permissions(self.request(self.non_admin_user), mortal, mortal_profile)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        staff = self.create_user("staff", account=self.account, is_staff=True)
        self.assertIsNone(user_views.eval_permissions(self.request(staff), mortal, mortal_profile))
        self.assertIsNone(user_views.eval_permissions(self.request(mortal), mortal, mortal_profile))

    def test_get_user_for_operation(self):
        response = user_views.get_user_for_operation(self.request(AnonymousUser()), self.non_admin_user.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)  # type: ignore[union-attr]
        response = user_views.get_user_for_operation(self.request(self.admin_user), 999999999)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)  # type: ignore[union-attr]
        homeless = self.create_user("homeless")
        response = user_views.get_user_for_operation(self.request(self.admin_user), homeless.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)  # type: ignore[union-attr]
        user, user_profile = user_views.get_user_for_operation(self.request(self.admin_user), self.non_admin_user.id)  # type: ignore[arg-type,misc]
        self.assertEqual(user, self.non_admin_user)
        self.assertEqual(user_profile, self.non_admin_user_profile)

    def test_get_user(self):
        """Test that staff get users within their account, and mortals only themselves."""
        response = user_views.get_user(self.request(self.non_admin_user, method="get"))
        self.assertEqual(response.data["username"], self.non_admin_user.username)  # type: ignore[union-attr]

        response = user_views.get_user(self.request(AnonymousUser(), method="get"), self.non_admin_user.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        staff = self.create_user("staff", account=self.account, is_staff=True)
        response = user_views.get_user(self.request(staff, method="get"), self.non_admin_user.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data["username"], self.non_admin_user.username)  # type: ignore[union-attr]

        mortal = self.create_user("mortal", account=self.account)
        response = user_views.get_user(self.request(mortal, method="get"), self.non_admin_user.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        response = user_views.get_user(self.request(mortal, method="get"), mortal.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_user_refusals(self):
        """Test that create_user() refuses mortals, staff without an account, and a duplicate username."""
        body = json.dumps({"username": f"new_{self.hash_suffix}", "password": "pw"})
        response = user_views.create_user(self.request(AnonymousUser(), body))
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        response = user_views.create_user(self.request(self.non_admin_user, body))
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        response = user_views.create_user(self.request(self.admin_user, "not json"))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        homeless_staff = self.create_user("homeless_staff", is_staff=True)
        response = user_views.create_user(self.request(homeless_staff, body))
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        duplicate = json.dumps({"username": self.non_admin_user.username, "password": "pw"})
        response = user_views.create_user(self.request(self.admin_user, duplicate))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_update_user_refusals(self):
        """Test that update_user() refuses bad bodies, users without a profile, and failed saves."""
        response = user_views.update_user(self.request(self.admin_user, "not json", "patch"), self.non_admin_user.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response = user_views.update_user(self.request(self.admin_user, "[1]", "patch"), self.non_admin_user.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        homeless = self.create_user("homeless")
        response = user_views.update_user(self.request(self.admin_user, "{}", "patch"), homeless.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        mortal = self.create_user("mortal", account=self.account)
        response = user_views.update_user(self.request(self.non_admin_user, "{}", "patch"), mortal.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        body = json.dumps({"first_name": "Ada"})
        with patch.object(User, "save", side_effect=ValidationError("invalid user")):
            response = user_views.update_user(self.request(self.admin_user, body, "patch"), mortal.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        with patch.object(User, "save", side_effect=RuntimeError("boom")):
            response = user_views.update_user(self.request(self.admin_user, body, "patch"), mortal.id)  # type: ignore[arg-type]
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
