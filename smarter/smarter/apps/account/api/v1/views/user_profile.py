# pylint: disable=W0707,W0718
"""UserProfile views for smarter api."""

from http import HTTPStatus
from typing import Optional

from django.db import transaction
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

import smarter.lib.logging as logging
from smarter.apps.account.models import UserProfile
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


# pylint: disable=W0613
class UserProfileView(AccountViewBase):
    """UserProfile view for smarter api."""

    def get(self, request: Request, user_profile_id: int):
        if user_profile_id and request.user.is_superuser:  # type: ignore
            self.user_profile = get_object_or_404(UserProfile, pk=user_profile_id)
        else:
            return Http404()

    def post(self, request: Request):
        return HttpResponseBadRequest()

    def patch(self, request: Request, user_profile_id: Optional[int] = None):
        return HttpResponseBadRequest()

    def delete(self, request, user_profile_id: int):
        if user_profile_id and self.is_superuser_or_unauthorized():
            self.user_profile = get_object_or_404(UserProfile, pk=user_profile_id)
        else:
            return HttpResponseForbidden()

        try:
            with transaction.atomic():
                if not isinstance(self.user_profile, UserProfile):
                    return JsonResponse({"error": "UserProfile not found"}, status=HTTPStatus.NOT_FOUND)
                self.user_profile.delete()
                UserProfile.objects.get(user=request.user).delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class UserProfileListView(AccountListViewBase):
    """UserProfile list view for smarter api."""

    def get_queryset(self):
        if not isinstance(self.user_profile, UserProfile):
            return UserProfile.objects.none()
        if not self.request:
            return UserProfile.objects.none()
        if not self.request.user.is_authenticated:  # type: ignore
            return UserProfile.objects.none()
        if self.request.user.is_superuser:  # type: ignore
            return UserProfile.objects.all()
        return self.user_profile.cached_account
