# pylint: disable=W0707,W0718
"""Account views for smarter api."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class AccountView(AccountViewBase):
    """Account view for smarter api."""

    def get(self, request: Request, account_id: int):
        if account_id and request.user.is_superuser:  # type: ignore
            self.account = get_object_or_404(Account, pk=account_id)
        else:
            if not isinstance(self.user_profile, UserProfile):
                return JsonResponse({"error": "User profile not found"}, status=HTTPStatus.UNAUTHORIZED)
            self.account = self.user_profile.account
        serializer = self.serializer_class(self.account)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request):
        try:
            data = json.loads(request.body.decode("utf-8"))
            name = data.get("name", data.get("account_number", "company_name")) or "Default_Account_Name"
            data["name"] = name.replace(" ", "_").replace("-", "_").lower()
            with transaction.atomic():
                self.account = Account.objects.create(**data)
                UserProfile.objects.create(name=request.user.username, user=request.user, account=self.account)  # type: ignore
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(self.account.id) + "/")  # type: ignore

    def patch(self, request: Request, account_id: Optional[int] = None):
        data: dict

        if not isinstance(request.data, dict):
            return JsonResponse(
                {
                    "error": f"Invalid request data. Expected a JSON dict in request body but received {type(request.data)}"
                },
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            if account_id and self.is_superuser_or_unauthorized():
                self.account = Account.get_cached_object(pk=account_id)
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
                if hasattr(self.account, key):
                    setattr(self.account, key, value)
            if not isinstance(self.account, Account):
                return JsonResponse({"error": "Account not found"}, status=HTTPStatus.NOT_FOUND)
            self.account.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request, account_id: int):
        if account_id and self.is_superuser_or_unauthorized():
            self.account = get_object_or_404(Account, pk=account_id)

        try:
            with transaction.atomic():
                if not isinstance(self.account, Account):
                    return JsonResponse({"error": "Account not found"}, status=HTTPStatus.NOT_FOUND)
                self.account.delete()
                UserProfile.objects.get(user=request.user).delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class AccountListView(AccountListViewBase):
    """Account list view for smarter api."""

    def get_queryset(self):
        if not isinstance(self.user_profile, UserProfile):
            return Account.objects.none()
        if not self.request:
            return Account.objects.none()
        if not self.request.user.is_authenticated:  # type: ignore
            return Account.objects.none()
        if self.request.user.is_superuser:  # type: ignore
            return Account.objects.all()
        return self.user_profile.cached_account
