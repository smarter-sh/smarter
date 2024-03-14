# -*- coding: utf-8 -*-
"""Views for the account settings."""
import logging
from http import HTTPStatus

from django import forms, http
from django.contrib.auth import get_user_model

from smarter.apps.account.models import UserProfile
from smarter.view_helpers import SmarterAdminWebView


User = get_user_model()
logger = logging.getLogger(__name__)
excluded_fields = ["password", "date_joined"]


class UserForm(forms.ModelForm):
    """Form for User edits."""

    class Meta:
        """Meta class for UserForm with all fields."""

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
        user_account = UserProfile.objects.get(user=request.user).account
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

    def _handle_write(self, request, user_id):
        target_user = User.objects.get(id=user_id)
        target_user_profile = UserProfile.objects.get(user=target_user)
        user_profile = UserProfile.objects.get(user=request.user)
        if target_user_profile.account != user_profile.account:
            return http.JsonResponse(
                status=HTTPStatus.FORBIDDEN, data={"User": "User not associated with your account."}
            )

        user_form = UserForm(request.POST, instance=target_user)
        if user_form.is_valid():
            user_form.save()
            return http.JsonResponse(status=HTTPStatus.OK, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=user_form.errors)

    # pylint: disable=W0221
    def get(self, request, user_id):
        user = User.objects.get(id=user_id)
        user_form = UserForm(instance=user)
        context = {
            "account_users": {
                "user": user,
                "user_form": user_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, user_id):
        return self._handle_write(request, user_id)

    def patch(self, request, user_id):
        return self._handle_write(request, user_id)

    def put(self, request, user_id):
        return self._handle_write(request, user_id)
