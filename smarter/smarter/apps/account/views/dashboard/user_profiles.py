"""
Views for the user menu's **Change Profile** item, in the ``@smarter/dashboard-user-menu`` React app.

A user can have more than one UserProfile, one per account, e.g. a student who is enrolled in two
courses at once. The web console acts as one of them at a time: the one that the user chose, for this
session, else their newest. See :mod:`smarter.apps.account.profile_selection`.

- ``user-profiles/`` lists the user's profiles, and which one the console acts as.
- ``user-profiles/select/`` chooses the one that it acts as, for the rest of the session.
"""

from datetime import datetime
from http import HTTPStatus

from django import http
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic.alias_generators import to_camel

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.account.profile_selection import SELECTED_USER_PROFILE_SESSION_KEY
from smarter.lib import json, logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class UserProfilesModel(BaseModel):
    """The base class of these views' models: camelCase JSON, and no fields that a model doesn't define."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class UserProfileChoice(UserProfilesModel):
    """
    One of the user's profiles, as the Change Profile dialog lists it.

    :param id: The UserProfile's primary key, which the select view takes.
    :param account_number: The account's number, e.g. ``1234-5678-9012``.
    :param account_name: The account's name, its company name.
    :param created_at: When the UserProfile was created: when the user joined the account.
    :param is_current: Whether the web console acts as this profile.
    """

    id: int
    account_number: str
    account_name: str
    created_at: datetime
    is_current: bool


class UserProfilesApiResponse(UserProfilesModel):
    """
    The response of both views: the user's profiles, newest first.

    :param user_profiles: The user's profiles.
    """

    user_profiles: list[UserProfileChoice]

    @classmethod
    def for_user(cls, user: User, current_id: int | None) -> "UserProfilesApiResponse":
        """
        The user's profiles, newest first.

        :param user: The Django user.
        :type user: django.contrib.auth.models.User
        :param current_id: The id of the profile that the web console acts as.
        :type current_id: int | None
        :returns: The response.
        :rtype: UserProfilesApiResponse
        """
        user_profiles = UserProfile.objects.filter(user=user).select_related("account").order_by("-pk")
        return cls(
            user_profiles=[
                UserProfileChoice(
                    id=user_profile.pk,
                    account_number=user_profile.account.account_number,
                    account_name=user_profile.account.company_name,
                    created_at=user_profile.created_at,
                    is_current=user_profile.pk == current_id,
                )
                for user_profile in user_profiles
            ]
        )


class UserProfileSelectRequest(UserProfilesModel):
    """
    The body of a request to the select view.

    :param user_profile_id: The id of the profile that the web console is to act as.
    """

    user_profile_id: int


def not_signed_in() -> http.JsonResponse:
    """
    The response to a request without a signed-in user.

    :class:`~smarter.lib.django.views.SmarterAuthenticatedNeverCachedWebView` redirects anonymous
    requests to the login page, so this is only for a user that :func:`get_resolved_user` can't resolve.

    :returns: A 401 response.
    :rtype: django.http.JsonResponse
    """
    return http.JsonResponse({"error": "Not signed in."}, status=HTTPStatus.UNAUTHORIZED)


class UserProfilesView(SmarterAuthenticatedNeverCachedWebView):
    """
    Lists the user's profiles, newest first, and which one the web console acts as.

    Response shape:

    .. code-block:: json

        {
            "userProfiles": [
                {
                    "id": 12,
                    "accountNumber": "1234-5678-9012",
                    "accountName": "Introduction to Prompt Engineering",
                    "createdAt": "2026-09-01T14:03:00Z",
                    "isCurrent": true
                }
            ]
        }
    """

    def post(self, request, *args, **kwargs) -> http.JsonResponse:
        user = get_resolved_user(request.user)
        if not isinstance(user, User):
            return not_signed_in()
        try:
            current = UserProfile.get_cached_object(user=user)
        except UserProfile.DoesNotExist:
            current = None
        response = UserProfilesApiResponse.for_user(user, current.pk if current else None)
        return http.JsonResponse(response.model_dump(mode="json"), status=HTTPStatus.OK)


class UserProfileSelectView(SmarterAuthenticatedNeverCachedWebView):
    """
    Chooses the profile that the web console acts as, for the rest of the session.

    The body is a :class:`UserProfileSelectRequest`, as JSON. The profile must be one of the user's.
    Its id is stored in the session, under
    :data:`~smarter.apps.account.profile_selection.SELECTED_USER_PROFILE_SESSION_KEY`. The response is
    that of :class:`UserProfilesView`, with the chosen profile current. The React app reloads the page,
    so that everything on it belongs to the chosen profile's account.
    """

    def post(self, request, *args, **kwargs) -> http.JsonResponse:
        user = get_resolved_user(request.user)
        if not isinstance(user, User):
            return not_signed_in()
        try:
            body = UserProfileSelectRequest.model_validate(json.loads(request.body or b"{}"))
        except (ValueError, ValidationError) as e:
            logger.warning("%s.post() invalid body from user %s: %s", self.formatted_class_name, user.pk, e)
            return http.JsonResponse({"error": "Invalid request body."}, status=HTTPStatus.BAD_REQUEST)
        if not UserProfile.objects.filter(pk=body.user_profile_id, user=user).exists():
            logger.warning(
                "%s.post() user %s chose UserProfile %s, which isn't theirs",
                self.formatted_class_name,
                user.pk,
                body.user_profile_id,
            )
            return http.JsonResponse({"error": "Not one of your profiles."}, status=HTTPStatus.NOT_FOUND)
        request.session[SELECTED_USER_PROFILE_SESSION_KEY] = body.user_profile_id
        logger.info("%s.post() user %s chose UserProfile %s", self.formatted_class_name, user.pk, body.user_profile_id)
        response = UserProfilesApiResponse.for_user(user, body.user_profile_id)
        return http.JsonResponse(response.model_dump(mode="json"), status=HTTPStatus.OK)
