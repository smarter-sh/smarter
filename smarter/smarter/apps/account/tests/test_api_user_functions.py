"""
Test the functions of the user api view, :mod:`smarter.apps.account.api.v1.views.user`, for each role.

The view itself is limited to superusers by SmarterAdminAPIView, so the functions are called
directly, to test their branches for staff users and customers too.
"""

from http import HTTPStatus

from django.contrib.auth.models import AnonymousUser, User
from django.http import JsonResponse
from django.test import RequestFactory

from smarter.apps.account.api.v1.views import user as user_api
from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib import json


class TestUserApiFunctions(TestAccountMixin):
    """Test get_user(), create_user(), update_user(), delete_user() and their helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staff_user, _, cls.staff_user_profile = mortal_user_factory(account=cls.account)
        cls.staff_user.is_staff = True
        cls.staff_user.save()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(pk=cls.staff_user.pk).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def request(self, user, method="get", body=None, path="/api/v1/account/users/"):
        request = getattr(self.factory, method)(
            path, data=json.dumps(body) if body is not None else None, content_type="application/json"
        )
        request.user = user
        return request

    def test_validate_request_body(self):
        self.assertIsNone(
            user_api.validate_request_body(self.request(self.admin_user, "post", {"username": "a", "password": "b"}))
        )
        for body in ([], {"password": "b"}, {"username": "a"}):
            with self.subTest(body=body):
                response = user_api.validate_request_body(self.request(self.admin_user, "post", body))
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        request = self.factory.post("/", data="not json", content_type="application/json")
        self.assertEqual(user_api.validate_request_body(request).status_code, HTTPStatus.BAD_REQUEST)

    def test_eval_permissions(self):
        self.assertIsNone(
            user_api.eval_permissions(self.request(self.admin_user), self.non_admin_user, self.non_admin_user_profile)
        )
        self.assertIsNone(
            user_api.eval_permissions(self.request(self.staff_user), self.non_admin_user, self.non_admin_user_profile)
        )
        self.assertIsNone(
            user_api.eval_permissions(
                self.request(self.non_admin_user), self.non_admin_user, self.non_admin_user_profile
            )
        )
        response = user_api.eval_permissions(
            self.request(self.non_admin_user), self.staff_user, self.staff_user_profile
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        other_user, other_account, other_profile = mortal_user_factory()
        self.addCleanup(other_account.delete)
        self.addCleanup(other_user.delete)
        response = user_api.eval_permissions(self.request(self.staff_user), other_user, other_profile)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_get_user_for_operation(self):
        user, profile = user_api.get_user_for_operation(self.request(self.admin_user), self.non_admin_user.id)
        self.assertEqual((user, profile), (self.non_admin_user, self.non_admin_user_profile))
        self.assertIsInstance(user_api.get_user_for_operation(self.request(self.admin_user), 999999999), JsonResponse)
        self.assertIsInstance(
            user_api.get_user_for_operation(self.request(AnonymousUser()), self.non_admin_user.id), JsonResponse
        )

    def test_get_user(self):
        """Test that a superuser gets any user, staff a user of their account, and a customer only themself."""
        get = user_api.get_user
        self.assertEqual(get(self.request(self.non_admin_user)).data["username"], self.non_admin_user.username)
        self.assertEqual(
            get(self.request(self.admin_user), self.non_admin_user.id).data["username"], self.non_admin_user.username
        )
        self.assertEqual(get(self.request(self.admin_user), 999999999).status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            get(self.request(self.staff_user), self.non_admin_user.id).data["username"], self.non_admin_user.username
        )
        self.assertEqual(get(self.request(self.non_admin_user), self.non_admin_user.id).status_code, HTTPStatus.OK)
        self.assertEqual(
            get(self.request(self.non_admin_user), self.staff_user.id).status_code, HTTPStatus.UNAUTHORIZED
        )
        self.assertEqual(get(self.request(AnonymousUser()), self.staff_user.id).status_code, HTTPStatus.UNAUTHORIZED)

    def test_create_update_and_delete_user(self):
        username = "test_api_functions_user"
        self.addCleanup(User.objects.filter(username=username).delete)
        response = user_api.create_user(
            self.request(self.admin_user, "post", {"username": username, "password": "pw-12345"})
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        user = User.objects.get(username=username)
        self.assertEqual(UserProfile.objects.get(user=user).account, self.account)

        response = user_api.update_user(self.request(self.admin_user, "patch", {"first_name": "Renamed"}), user.id)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(User.objects.get(pk=user.pk).first_name, "Renamed")

        path = f"/api/v1/account/users/{user.id}/"
        response = user_api.delete_user(self.request(self.admin_user, "delete", path=path), user.id)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_create_user_errors(self):
        body = {"username": self.admin_user.username, "password": "x"}
        self.assertEqual(
            user_api.create_user(self.request(self.non_admin_user, "post", body)).status_code, HTTPStatus.UNAUTHORIZED
        )
        self.assertEqual(
            user_api.create_user(self.request(AnonymousUser(), "post", body)).status_code, HTTPStatus.UNAUTHORIZED
        )
        # the username already exists.
        self.assertEqual(
            user_api.create_user(self.request(self.admin_user, "post", body)).status_code, HTTPStatus.BAD_REQUEST
        )
        request = self.factory.post("/", data="not json", content_type="application/json")
        request.user = self.admin_user
        self.assertEqual(user_api.create_user(request).status_code, HTTPStatus.BAD_REQUEST)

    def test_update_unknown_user(self):
        """Test that updating a user that doesn't exist is a 400."""
        self.assertEqual(
            user_api.update_user(self.request(self.admin_user, "patch", {}), 999999999).status_code,
            HTTPStatus.BAD_REQUEST,
        )

    def test_permissions_are_enforced(self):
        """Test that a customer may not update or delete another user, and may not make themself a superuser."""
        response = user_api.update_user(
            self.request(self.non_admin_user, "patch", {"first_name": "X"}), self.staff_user.id
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        response = user_api.delete_user(self.request(self.non_admin_user, "delete"), self.staff_user.id)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertTrue(User.objects.filter(pk=self.staff_user.pk).exists())
        self.addCleanup(User.objects.filter(pk=self.non_admin_user.pk).update, is_superuser=False)
        user_api.update_user(self.request(self.non_admin_user, "patch", {"is_superuser": True}), self.non_admin_user.id)
        self.assertFalse(User.objects.get(pk=self.non_admin_user.pk).is_superuser)
        self.assertEqual(
            user_api.update_user(self.request(self.admin_user, "patch", []), self.non_admin_user.id).status_code,
            HTTPStatus.BAD_REQUEST,
        )
        response = user_api.eval_permissions(self.request(AnonymousUser()), self.staff_user)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_create_user_fields_are_restricted(self):
        """Test that the request body can't create a superuser, and an invalid body is refused."""
        username = "test_api_functions_restricted"
        self.addCleanup(User.objects.filter(username=username).delete)
        body = {"username": username, "password": "pw-12345", "is_superuser": True, "is_staff": True}
        user_api.create_user(self.request(self.admin_user, "post", body))
        user = User.objects.get(username=username)
        self.assertFalse(user.is_superuser or user.is_staff)
        response = user_api.create_user(self.request(self.admin_user, "post", {"username": "missing_password"}))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_update_and_delete_errors(self):
        request = self.factory.patch("/", data="not json", content_type="application/json")
        request.user = self.admin_user
        self.assertEqual(user_api.update_user(request, self.non_admin_user.id).status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            user_api.delete_user(self.request(self.admin_user, "delete"), 999999999).status_code, HTTPStatus.NOT_FOUND
        )
