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

from smarter.apps.account.contract.models import AccountApiProfile
from smarter.apps.account.models import UserProfile
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


# pylint: disable=W0613
class UserProfileView(AccountViewBase):
    """UserProfile view for smarter api.

    Its ``GET`` returns an :class:`AccountApiProfile`.
    """

    def get(self, request: Request, user_profile_id: int):
        """
        Return a UserProfile as json.

        :param request: The request.
        :param user_profile_id: The UserProfile's id.
        :returns: The :class:`AccountApiProfile` of the UserProfile.
        :raises Http404: when the UserProfile does not exist.
        """
        user_profile = get_object_or_404(UserProfile.objects.select_related("user", "account"), pk=user_profile_id)
        return JsonResponse(AccountApiProfile.from_model(user_profile).model_dump(mode="json"))

    def post(self, request: Request, user_profile_id: Optional[int] = None):
        """
        Refuse to create a UserProfile: this endpoint does not support it.

        :param request: The request.
        :param user_profile_id: Unused.
        :returns: A 400 response.
        """
        return HttpResponseBadRequest()

    def patch(self, request: Request, user_profile_id: Optional[int] = None):
        """
        Refuse to update a UserProfile: this endpoint does not support it.

        :param request: The request.
        :param user_profile_id: Unused.
        :returns: A 400 response.
        """
        return HttpResponseBadRequest()

    def delete(self, request, user_profile_id: int):
        """
        Delete a UserProfile.

        :param request: The request.
        :param user_profile_id: The UserProfile's id.
        :returns: A redirect to ``/``, or a 500 :class:`JsonResponse` when the delete fails.
        :raises Http404: when the UserProfile does not exist.
        """
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


class UserProfileListView(ContractListMixin, AccountListViewBase):
    """UserProfile list view for smarter api: :class:`AccountApiProfile` models."""

    contract_model = AccountApiProfile

    def get_queryset(self):
        """
        Return every UserProfile for a superuser, else those of the request user's Account.

        :returns: The queryset, ordered by pk; empty for an anonymous request or a user without a UserProfile.
        """
        if not isinstance(self.user_profile, UserProfile):
            return UserProfile.objects.none()
        if not self.request:
            return UserProfile.objects.none()
        if not self.request.user.is_authenticated:  # type: ignore
            return UserProfile.objects.none()
        user_profiles = UserProfile.objects.select_related("user", "account").order_by("pk")
        if self.request.user.is_superuser:  # type: ignore
            return user_profiles
        return user_profiles.filter(account=self.user_profile.account)
