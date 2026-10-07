"""Test the error branches of the user api handlers and views, :mod:`smarter.apps.account.api.v1.views.user`."""

from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch

from django.http import Http404, JsonResponse
from rest_framework.response import Response

from smarter.apps.account.api.v1.views import user as user_views
from smarter.apps.account.api.v1.views.user import UserListView, UserView
from smarter.apps.account.tests.mixins import TestAccountMixin

MODULE = "smarter.apps.account.api.v1.views.user"


class TestUserViewBranches(TestAccountMixin):
    """Test the user api's handling of unknown users, missing profiles and failures."""

    def request(self, user=None, body: bytes = b"{}") -> MagicMock:
        request = MagicMock()
        request.user = user or self.admin_user
        request.body = body
        request.path_info = "/api/v1/account/users/"
        return request

    def test_request_body_that_cannot_be_read(self):
        with patch(f"{MODULE}.json.loads", side_effect=RuntimeError("unreadable")):
            response = user_views.validate_request_body(self.request())
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_get_user_without_a_resolved_user(self):
        with patch(f"{MODULE}.get_resolved_user", return_value=None):
            response = user_views.get_user(self.request(), user_id=1)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_get_user_by_staff_outside_their_account(self):
        staff = MagicMock(is_superuser=False, is_staff=True)
        with patch(f"{MODULE}.get_resolved_user", return_value=staff):
            response = user_views.get_user(self.request(user=self.non_admin_user), user_id=999999999)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_create_user_without_a_resolved_user(self):
        with patch(f"{MODULE}.get_resolved_user", return_value=None):
            response = user_views.create_user(self.request())
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_update_user_without_a_user_or_profile(self):
        for result in ((None, None), (self.non_admin_user, None)):
            with self.subTest(result=result):
                with patch(f"{MODULE}.get_user_for_operation", return_value=result):
                    response = user_views.update_user(self.request(), user_id=1)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_delete_user_defaults_to_the_requesting_user(self):
        forbidden = JsonResponse({}, status=HTTPStatus.FORBIDDEN)
        with patch(f"{MODULE}.eval_permissions", return_value=forbidden) as eval_permissions:
            response = user_views.delete_user(self.request(user=self.non_admin_user))
        self.assertIs(response, forbidden)
        self.assertEqual(eval_permissions.call_args.args[1], self.non_admin_user)

    def test_user_view_not_found(self):
        response = UserView().handle_exception(Http404("nope"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def list_view(self, user) -> UserListView:
        view = UserListView()
        view.request = self.request(user=user)
        return view

    def test_list_without_a_resolved_user(self):
        view = self.list_view(self.admin_user)
        with patch(f"{MODULE}.get_resolved_user", return_value=None):
            response = view.get_list(view.request)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_list_for_a_non_superuser(self):
        """A non-superuser lists the users of their own account."""
        view = self.list_view(self.non_admin_user)
        users = list(view.get_queryset().values_list("pk", flat=True))
        self.assertIn(self.non_admin_user.pk, users)
        self.assertIn(self.admin_user.pk, users)
