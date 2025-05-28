"""Views for the account settings."""

import json
import logging
from http import HTTPStatus

from django import forms, http
from django.db import transaction
from django.shortcuts import redirect

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.lib.django.user import User
from smarter.lib.django.view_helpers import SmarterAdminWebView


logger = logging.getLogger(__name__)
excluded_fields = ["password", "date_joined"]


class UserForm(forms.ModelForm):
    """Form for User edits."""

    class Meta:
        """Meta class for UserForm with editable fields."""

        model = User
        # pylint: disable=W0212
        fields = [f.name for f in User._meta.fields if f.name not in excluded_fields]


class UsersView(SmarterAdminWebView):
    """View for user management."""

    template_path = "account/dashboard/users.html"

    def get(self, request):
        """
        Get the users for the account, but exclude any superusers.
        """
        user_account = get_cached_user_profile(user=request.user).account
        user_ids = (
            UserProfile.objects.filter(account=user_account)
            .exclude(user__is_superuser=True)
            .values_list("user_id", flat=True)
        )
        users = User.objects.filter(id__in=user_ids)
        context = {
            "account_users": {
                "users": users,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class UserView(SmarterAdminWebView):
    """View for user management."""

    template_path = "account/dashboard/user.html"

    def get_body_json(self, request):
        return json.loads(request.body.decode("utf-8").replace("'", '"'))

    def _handle_create(self, request, data=None):
        user_profile = get_cached_user_profile(user=request.user)
        user_form = UserForm(data=data)
        if user_form.is_valid():
            target_user = user_form.save()
            target_user_profile = UserProfile.objects.create(user=target_user, account=user_profile.account)
            target_user_profile.save()
            return redirect("account:account_user", user_id=target_user.id)
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data=user_form.errors)

    def _handle_write(self, request, user_id, data=None):

        user_profile = get_cached_user_profile(user=request.user)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"User": "User not found."})

        target_user_profile = get_cached_user_profile(user=target_user)
        if target_user_profile.account != user_profile.account:
            return http.JsonResponse(
                status=HTTPStatus.FORBIDDEN.value, data={"User": "User not associated with your account."}
            )

        user_form = UserForm(data, instance=target_user)
        if user_form.is_valid():
            user_form.save()
            return http.JsonResponse(status=HTTPStatus.OK.value, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data=user_form.errors)

    # pylint: disable=W0221
    def get(self, request, user_id=None):
        """Get the user for the account. We also use this to create a new user."""
        try:
            user = User.objects.get(id=user_id)
            user_form = UserForm(instance=user)
        except User.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"User": "User not found."})

        context = {
            "account_users": {
                "user": user,
                "user_form": user_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, user_id=None):
        data = request.POST
        if user_id is None:
            return self._handle_create(request, data=data)
        return self._handle_write(request, user_id=user_id, data=data)

    def patch(self, request, user_id):
        data = self.get_body_json(request)
        return self._handle_write(request, user_id=user_id, data=data)

    def put(self, request, user_id=None):
        data = self.get_body_json(request)
        if user_id is None:
            return self._handle_create(request, data=data)
        return self._handle_write(request, user_id=user_id, data=data)

    def delete(self, request, user_id):
        user_profile = get_cached_user_profile(user=request.user)
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"User": "User not found."})

        target_user_profile = get_cached_user_profile(user=target_user)
        if target_user_profile.account != user_profile.account:
            return http.JsonResponse(
                status=HTTPStatus.FORBIDDEN.value, data={"User": "User not associated with your account."}
            )

        with transaction.atomic():
            target_user_profile.delete()
            target_user.delete()

        return http.JsonResponse(status=HTTPStatus.OK.value, data={})
