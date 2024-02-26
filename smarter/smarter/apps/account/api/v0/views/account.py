# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718
"""Account views for smarter api."""
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from knox.auth import TokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.serializers import AccountSerializer


@api_view(["GET", "POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def account_view(request, account_id: int = None):
    if request.method == "GET":
        return get_account(request, account_id)
    if request.method == "POST":
        return create_account(request)
    if request.method == "PATCH":
        return update_account(request, account_id)
    if request.method == "DELETE":
        return delete_account(request, account_id)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def accounts_list_view(request):
    """Get a json list[dict] of all accounts for the current user."""
    if not request.user.is_superuser:
        try:
            account = UserProfile.objects.get(user=request.user).account
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        serializer = AccountSerializer(account)
        return Response(serializer.data, status=HTTPStatus.OK)

    accounts = Account.objects.all()
    serializer = AccountSerializer(accounts, many=True)
    return Response(serializer.data, status=HTTPStatus.OK)


# -----------------------------------------------------------------------
# handlers for accounts
# -----------------------------------------------------------------------
def get_account(request, account_id: int = None):
    """Get an account json representation by id."""
    try:
        if account_id:
            account = Account.objects.get(id=account_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    serializer = AccountSerializer(account)
    return Response(serializer.data, status=HTTPStatus.OK)


def create_account(request):
    """Create an account from a json representation in the body of the request."""
    data: dict = None

    try:
        data = request.data
        with transaction.atomic():
            account = Account.objects.create(**data)
            UserProfile.objects.create(user=request.user, account=account)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    return HttpResponseRedirect(request.path_info + str(account.id) + "/")


def update_account(request, account_id: int = None):
    """update an account from a json representation in the body of the request."""
    account: Account = None
    data: dict = None

    try:
        if account_id:
            account = Account.objects.get(id=account_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        data = request.data
        if not isinstance(data, dict):
            return JsonResponse(
                {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    try:
        for key, value in data.items():
            if hasattr(account, key):
                setattr(account, key, value)
        account.save()
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return HttpResponseRedirect(request.path_info)


def delete_account(request, account_id: int = None):
    """delete a plugin by id."""
    try:
        if account_id:
            account = Account.objects.get(id=account_id)
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
