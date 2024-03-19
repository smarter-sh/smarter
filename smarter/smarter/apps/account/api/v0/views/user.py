# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718
"""User views for smarter api."""
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseRedirect, JsonResponse
from rest_framework import status
from rest_framework.response import Response

from smarter.apps.account.api.v0.serializers import UserSerializer
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.common.view_helpers import (
    SmarterAPIAdminView,
    SmarterAPIListAdminView,
)


User = get_user_model()


class UserView(SmarterAPIAdminView):
    """User view for smarter api."""

    def get(self, request, user_id: int):
        return get_user(request, user_id)

    def post(self, request):
        return create_user(request)

    def patch(self, request):
        return update_user(request)

    def delete(self, request, user_id):
        return delete_user(request, user_id)

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"error": "Invalid HTTP method"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().handle_exception(exc)


class UserListView(SmarterAPIListAdminView):
    """User list view for smarter api."""

    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()

        try:
            account_users = UserProfile.objects.filter(account__user=self.request.user).values_list("user", flat=True)
            return User.objects.filter(id__in=account_users)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not found"}, status=HTTPStatus.NOT_FOUND)


# -----------------------------------------------------------------------
# handlers for users
# -----------------------------------------------------------------------


def validate_request_body(request):
    # do a cursory check of the request data
    try:
        if not isinstance(request.data, dict):
            raise ValidationError(
                f"Invalid request data. Was expecting a dictionary but received {type(request.data)}."
            )
        if "username" not in request.data:
            raise ValidationError("Invalid request data. Missing 'username' field.")
        if "password" not in request.data:
            raise ValidationError("Invalid request data. Missing 'password' field.")
    except ValidationError as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
    return None


def eval_permissions(request, user_to_update: User, user_to_update_profile: UserProfile = None):
    if not request.user.is_superuser:
        # if the user is not a superuser then they need to have a UserProfile
        try:
            request_user_account = UserProfile.objects.get(user=request.user).account
        except UserProfile.DoesNotExist:
            return JsonResponse(
                {"error": "You are not authorized to modify Smarter user accounts."}, status=HTTPStatus.UNAUTHORIZED
            )

        # if the user is not a superuser then at most they can update users within their own account
        if user_to_update_profile and user_to_update_profile.account != request_user_account:
            return JsonResponse(
                {"error": "You are not authorized to modify this user account."}, status=HTTPStatus.UNAUTHORIZED
            )

        # if the user is neither a superuser nor a staff member then they can only update their own account
        if not request.user.is_staff and user_to_update != request.user:
            return JsonResponse(
                {"error": "You are not authorized to modify this user account."}, status=HTTPStatus.UNAUTHORIZED
            )
    return None


def get_user_for_operation(request):
    user: User = None
    user_profile: UserProfile = None

    try:
        user = User.objects.get(id=request.data.get("id"))
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.BAD_REQUEST)

    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        pass

    return user, user_profile


# pylint: disable=too-many-return-statements
def get_user(request, user_id: int = None):
    """Get an account json representation by id."""
    user: User = None
    if user_id is None:
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=HTTPStatus.OK)

    # if the user is a superuser, they can get any user
    if request.user.is_superuser:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=HTTPStatus.NOT_FOUND)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=HTTPStatus.OK)

    # if the user is a staff member, they can get users within their own account
    if request.user.is_staff:
        try:
            account = UserProfile.objects.get(user=request.user).account
            user = UserProfile.objects.get(account=account, user_id=user_id).user
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=HTTPStatus.NOT_FOUND)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=HTTPStatus.OK)

    # mere mortals can only get their own account
    if user_id != request.user.id:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=HTTPStatus.OK)


def create_user(request):
    """Create an account from a json representation in the body of the request."""
    account: Account = None
    data: dict = None
    if not request.user.is_superuser and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    validate_request_body(request)
    data = request.data

    # the new user will be associated with the account of the current user
    try:
        account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User is not associated with any account."}, status=HTTPStatus.UNAUTHORIZED)

    try:
        with transaction.atomic():
            user = User.objects.create_user(**data)
            user.save()
            UserProfile.objects.create(user=request.user, account=account)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    return HttpResponseRedirect(request.path_info + str(user.id) + "/")


def update_user(request):
    """update an account from a json representation in the body of the request."""
    data: dict = None
    user_to_update: User = None
    user_to_update_profile: UserProfile = None

    validate_request_body(request)
    data = request.data
    user_to_update, user_to_update_profile = get_user_for_operation(request)
    eval_permissions(request, user_to_update, user_to_update_profile)

    try:
        for key, value in data.items():
            if hasattr(user_to_update, key):
                setattr(user_to_update, key, value)
        user_to_update.save()
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return HttpResponseRedirect(request.path_info)


def delete_user(request, user_id: int = None):
    """delete a plugin by id."""
    try:
        if user_id:
            account = Account.objects.get(id=user_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        with transaction.atomic():
            account.delete()
            UserProfile.objects.get(user=request.user).delete()
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    plugins_path = request.path_info.rsplit("/", 2)[0]
    return HttpResponseRedirect(plugins_path)
