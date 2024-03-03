# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718
"""Account views for smarter api."""
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.account.api.v0.serializers import AccountSerializer
from smarter.apps.account.models import Account, UserProfile
from smarter.view_helpers import SmarterAPIAdminView, SmarterAPIListAdminView


class AccountView(SmarterAPIAdminView):
    """Account view for smarter api."""

    def get(self, request, account_id: int):
        return get_account(request, account_id)

    def post(self, request):
        return create_account(request)

    def patch(self, request, account_number: str = None):
        return update_account(request, account_number)

    def delete(self, request, account_number: str = None):
        return delete_account(request, account_number)


class AccountListView(SmarterAPIListAdminView):
    """Account list view for smarter api."""

    serializer_class = AccountSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Account.objects.all()

        try:
            return UserProfile.objects.get(user=self.request.user).account
        except UserProfile.DoesNotExist:
            return Response({"error": "User not found"}, status=HTTPStatus.NOT_FOUND)


# -----------------------------------------------------------------------
# handlers for accounts
# -----------------------------------------------------------------------
def get_account(request, account_id: int = None):
    """Get an account json representation by id."""
    if account_id and request.user.is_superuser:
        account = get_object_or_404(Account, pk=account_id)
    else:
        account = get_object_or_404(UserProfile, user=request.user).account
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
    if account_id:
        account = get_object_or_404(Account, pk=account_id)
    else:
        account = get_object_or_404(UserProfile, user=request.user).account

    try:
        with transaction.atomic():
            account.delete()
            UserProfile.objects.get(user=request.user).delete()
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    plugins_path = request.path_info.rsplit("/", 2)[0]
    return HttpResponseRedirect(plugins_path)
