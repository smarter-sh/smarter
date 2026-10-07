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

from smarter.apps.account.models import UserProfile
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


# pylint: disable=W0613
class UserProfileView(AccountViewBase):
    """UserProfile view for smarter api."""

    def get(self, request: Request, user_profile_id: int):
        self.user_profile = get_object_or_404(UserProfile, pk=user_profile_id)

    def post(self, request: Request, user_profile_id: Optional[int] = None):
        return HttpResponseBadRequest()

    def patch(self, request: Request, user_profile_id: Optional[int] = None):
        return HttpResponseBadRequest()

    def delete(self, request, user_profile_id: int):
        logger.debug(
            "%s.delete() called by %s with user_profile_id: %s",
            self.formatted_class_name,
            self.user_profile,
            user_profile_id,
        )
        user_profile = get_object_or_404(UserProfile, pk=user_profile_id)

        try:
            user_profile.delete()
        except Exception as e:
            logger.error("Error deleting user profile with id %s: %s", user_profile_id, str(e))
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect("/")


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
