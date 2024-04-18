# pylint: disable=W0707,W0718
"""Account views for smarter api."""
import logging
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile

from .base import AccountListViewBase, AccountViewBase


logger = logging.getLogger(__name__)


class AccountView(AccountViewBase):
    """Account view for smarter api."""

    def get(self, request, account_id: int):
        if account_id and request.user.is_superuser:
            account = get_object_or_404(Account, pk=account_id)
        else:
            account = self.user_profile.account
        serializer = self.serializer_class(account)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request):
        try:
            data = request.data
            with transaction.atomic():
                account = Account.objects.create(**data)
                UserProfile.objects.create(user=request.user, account=account)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(account.id) + "/")

    def patch(self, request, account_id: int = None):
        account: Account = None
        data: dict = None

        try:
            if account_id and self.is_superuser_or_unauthorized():
                account = Account.objects.get(id=account_id)
            else:
                account = self.user_profile.account
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
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request, account_id: int = None):
        if account_id and self.is_superuser_or_unauthorized():
            account = get_object_or_404(Account, pk=account_id)
        else:
            account = self.user_profile.account

        try:
            with transaction.atomic():
                account.delete()
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
        if self.request.user.is_superuser:
            return Account.objects.all()
        return self.user_profile.account
