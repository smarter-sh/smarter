# pylint: disable=W0707,W0718,W0613
"""User views for smarter api."""
import logging
from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseRedirect, JsonResponse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.account.serializers import UserSerializer
from smarter.apps.api.signals import api_request_completed
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import smarter_build_absolute_uri
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import AccountListViewBase, AccountViewBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class UserView(AccountViewBase):
    """User view for smarter api."""

    def get(self, request, user_id: int):
        logger.info("%s.get() - user_id: %s, request: %s", self.formatted_class_name, user_id, request)
        response = get_user(request, user_id)
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return response

    def post(self, request):
        logger.info("%s.post() - request: %s", self.formatted_class_name, request)
        response = create_user(request)
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return response

    def patch(self, request):
        logger.info("%s.patch() - request: %s", self.formatted_class_name, request)
        response = update_user(request)
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return response

    def delete(self, request, user_id):
        logger.info("%s.delete() - user_id: %s, request: %s", self.formatted_class_name, user_id, request)
        response = delete_user(request, user_id)
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return response

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            logger.info("%s.handle_exception() - Http404: %s", self.formatted_class_name, exc)
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        logger.error("%s.handle_exception() - unhandled exception: %s", self.formatted_class_name, exc)
        return super().handle_exception(exc)


class UserListView(AccountListViewBase):
    """User list view for smarter api."""

    serializer_class = UserSerializer

    def setup(self, request: Request, *args, **kwargs):
        """
        Setup the view. This is called by Django before dispatch() and is used to
        initialize attributes that require the request object.
        """
        super().setup(request, *args, **kwargs)
        logger.info(
            "%s.setup() - request: %s, user: %s, user_profile: %s is_authenticated: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            self.request.user.is_authenticated,
        )

    def get_queryset(self):
        logger.info("%s.get_queryset() - request: %s", self.formatted_class_name, self.request)
        user = get_resolved_user(self.request.user)
        if user is None:
            logger.info("%s.get_queryset() - user not found for request: %s", self.formatted_class_name, self.request)
            return Response({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
        if user.is_superuser:
            logger.info("%s.get_queryset() - user is superuser: %s", self.formatted_class_name, user)
            return User.objects.all()

        try:
            account_users = UserProfile.objects.filter(account__user=self.request.user).values_list("user", flat=True)
            logger.info(
                "%s.get_queryset() - account users for %s: %s", self.formatted_class_name, user, list(account_users)
            )
            return User.objects.filter(id__in=account_users)
        except UserProfile.DoesNotExist:
            logger.info("%s.get_queryset() - user profile not found for user: %s", self.formatted_class_name, user)
            return Response({"error": "User not found"}, status=HTTPStatus.NOT_FOUND.value)

    def get_list(self, request: Request):
        """
        Get a list of all users the requesting user has access to.
        """
        logger.info("%s.get() - request: %s", self.formatted_class_name, request)
        queryset = self.get_queryset()
        if isinstance(queryset, Response):
            return queryset
        serializer = UserSerializer(queryset, many=True)
        response = Response(serializer.data, status=HTTPStatus.OK.value)
        return response

    def get(self, request: Request, *args, **kwargs):
        """
        Handle GET requests to retrieve the list of users.
        """
        logger.info("%s.get() - request: %s", self.formatted_class_name, request)
        return self.get_list(request)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to create a new user.
        """
        logger.info("%s.post() - request: %s", self.formatted_class_name, request)
        return self.get_list(request)


# -----------------------------------------------------------------------
# handlers for users
# -----------------------------------------------------------------------


def validate_request_body(request: Request):
    # do a cursory check of the request data
    logger.info("%s.validate_request_body() - request body: %s", request.body)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValidationError(
                f"Invalid request data. Was expecting a dictionary but received {type(request.data) if hasattr(request, 'data') else 'unknown'}."
            )
        if "username" not in data:
            raise ValidationError("Invalid request data. Missing 'username' field.")
        if "password" not in data:
            raise ValidationError("Invalid request data. Missing 'password' field.")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format in request body."}, status=HTTPStatus.BAD_REQUEST.value)
    except ValidationError as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST.value)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST.value)
    return None


def eval_permissions(request, user_to_update: User, user_to_update_profile: Optional[UserProfile] = None):
    logger.info("%s.eval_permissions() - request: %s", request)
    user = get_resolved_user(request.user)
    if user is None:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
    if not user.is_superuser:
        # if the user is not a superuser then they need to have a UserProfile
        try:
            request_user_account = UserProfile.objects.get(user=request.user).account
        except UserProfile.DoesNotExist:
            return JsonResponse(
                {"error": "You are not authorized to modify Smarter user accounts."},
                status=HTTPStatus.UNAUTHORIZED.value,
            )

        # if the user is not a superuser then at most they can update users within their own account
        if user_to_update_profile and user_to_update_profile.account != request_user_account:
            return JsonResponse(
                {"error": "You are not authorized to modify this user account."}, status=HTTPStatus.UNAUTHORIZED.value
            )

        # if the user is neither a superuser nor a staff member then they can only update their own account
        if not request.user.is_staff and user_to_update != request.user:
            return JsonResponse(
                {"error": "You are not authorized to modify this user account."}, status=HTTPStatus.UNAUTHORIZED.value
            )
    return None


def get_user_for_operation(request) -> tuple[User, UserProfile] | JsonResponse:

    if not isinstance(request.user, User):
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED.value)

    try:
        user = User.objects.get(id=request.data.get("id"))
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.BAD_REQUEST.value)

    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User profile not found"}, status=HTTPStatus.BAD_REQUEST.value)

    logger.info("%s.get_user_for_operation() - user: %s", request, user)
    return user, user_profile


# pylint: disable=too-many-return-statements
def get_user(request, user_id: Optional[int] = None):
    """Get an account json representation by id."""
    logger.info("%s.get_user() - user_id: %s, request: %s", request, user_id, request)
    if user_id is None:
        serializer = UserSerializer(request.user)
        logger.info("UserListView.get_queryset() - returning current user: %s", request.user)
        return Response(serializer.data, status=HTTPStatus.OK.value)

    request_user = get_resolved_user(request.user)
    if request_user is None:
        logger.info("UserListView.get_queryset() - user not found for request: %s", self.request)
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
    # if the user is a superuser, they can get any user
    if request_user.is_superuser:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.info("UserListView.get_queryset() - user not found for id: %s", user_id)
            return JsonResponse({"error": "User not found"}, status=HTTPStatus.NOT_FOUND.value)
        serializer = UserSerializer(user)
        logger.info("UserListView.get_queryset() - returning user for id %s: %s", user_id, user)
        return Response(serializer.data, status=HTTPStatus.OK.value)

    # if the user is a staff member, they can get users within their own account
    if request_user.is_staff:
        try:
            account = UserProfile.objects.get(user=request.user).account
            user = UserProfile.objects.get(account=account, user_id=user_id).user
        except User.DoesNotExist:
            logger.info("UserListView.get_queryset() - user not found for id: %s", user_id)
            return JsonResponse({"error": "User not found"}, status=HTTPStatus.NOT_FOUND.value)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=HTTPStatus.OK)

    # mere mortals can only get their own account
    if user_id != request.user.id:
        logger.info("UserListView.get_queryset() - unauthorized access attempt for user id: %s", user_id)
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED.value)

    serializer = UserSerializer(request.user)
    logger.info("UserListView.get_queryset() - returning current user: %s", request.user)
    return Response(serializer.data, status=HTTPStatus.OK.value)


def create_user(request: Request):
    """Create an account from a json representation in the body of the request."""
    logger.info("%s.create_user() - request: %s", request, request)
    data: dict

    user = get_resolved_user(request.user)
    if user is None:
        logger.info("UserListView.get_queryset() - user not found for request: %s", request)
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
    if not user.is_superuser and not user.is_staff:
        logger.info("UserListView.get_queryset() - unauthorized access attempt for user: %s", user)
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED.value)

    validate_request_body(request)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.info("UserListView.get_queryset() - invalid JSON format in request body: %s", request.body)
        return JsonResponse({"error": "Invalid JSON format in request body."}, status=HTTPStatus.BAD_REQUEST.value)

    # the new user will be associated with the account of the current user
    try:
        account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        logger.info("UserListView.get_queryset() - user profile not found for user: %s", user)
        return JsonResponse({"error": "User is not associated with any account."}, status=HTTPStatus.UNAUTHORIZED.value)

    try:
        with transaction.atomic():
            user = User.objects.create_user(**data)
            UserProfile.objects.create(user=request.user, account=account)
    except Exception as e:
        logger.info("UserListView.get_queryset() - error creating user: %s", e)
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST.value)

    logger.info("UserListView.get_queryset() - user created successfully: %s", user)
    return HttpResponseRedirect(request.path_info + str(user.id) + "/")  # type: ignore[return-value]


def update_user(request: Request):
    """update an account from a json representation in the body of the request."""
    logger.info("%s.update_user() - request: %s", request, request)
    data: dict

    validate_request_body(request)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.info("UserListView.get_queryset() - invalid JSON format in request body: %s", request.body)
        return JsonResponse({"error": "Invalid JSON format in request body."}, status=HTTPStatus.BAD_REQUEST.value)
    user_to_update, user_to_update_profile = get_user_for_operation(request)
    if isinstance(user_to_update, JsonResponse):
        return user_to_update
    if isinstance(user_to_update_profile, JsonResponse):
        return user_to_update_profile

    if not isinstance(user_to_update, User):
        logger.info("UserListView.get_queryset() - user not found for request: %s", request)
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.BAD_REQUEST.value)
    if not isinstance(user_to_update_profile, UserProfile):
        logger.info("UserListView.get_queryset() - user profile not found for user: %s", user_to_update)
        return JsonResponse({"error": "User profile not found"}, status=HTTPStatus.BAD_REQUEST.value)
    eval_permissions(request, user_to_update, user_to_update_profile)

    try:
        for key, value in data.items():
            if hasattr(user_to_update, key):
                setattr(user_to_update, key, value)
        user_to_update.save()
        logger.info("UserListView.get_queryset() - user updated successfully: %s", user_to_update)
    except ValidationError as e:
        logger.info("UserListView.get_queryset() - validation error: %s", e)
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST.value)
    except Exception as e:
        logger.info("UserListView.get_queryset() - internal error: %s", e)
        return JsonResponse(
            {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR.value
        )

    return HttpResponseRedirect(request.path_info)


def delete_user(request: Request, user_id: Optional[int] = None):
    """delete a user by id."""
    logger.info("%s.delete_user() - user_id: %s, request: %s", request, user_id, request)
    try:
        if user_id:
            user = User.objects.get(id=user_id)
        else:
            user = request.user
    except User.DoesNotExist:
        logger.info("UserListView.get_queryset() - user not found for request: %s", self.request)
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.NOT_FOUND.value)

    try:
        with transaction.atomic():
            UserProfile.objects.get(user=user).delete()
            user.delete()
            logger.info("UserListView.get_queryset() - user deleted successfully: %s", user)
    except Exception as e:
        logger.info("UserListView.get_queryset() - error deleting user: %s", e)
        return JsonResponse(
            {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR.value
        )

    plugins_path = request.path_info.rsplit("/", 2)[0]

    return HttpResponseRedirect(plugins_path)
