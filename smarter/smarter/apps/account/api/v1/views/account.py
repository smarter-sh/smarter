# pylint: disable=W0707,W0718
"""Account views for smarter api."""

import logging
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile
from smarter.common.conf import settings as smarter_settings
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import AccountListViewBase, AccountViewBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class AccountView(AccountViewBase):
    """Account view for smarter api."""

    def get(self, request: WSGIRequest, account_id: int):
        if account_id and request.user.is_superuser:
            self.account = get_object_or_404(Account, pk=account_id)
        else:
            self.account = self.user_profile.account
        serializer = self.serializer_class(self.account)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: WSGIRequest):
        try:
            data = json.loads(request.body.decode("utf-8"))
            with transaction.atomic():
                self.account = Account.objects.create(**data)
                UserProfile.objects.create(user=request.user, account=self.account)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(self.account.id) + "/")

    def patch(self, request: WSGIRequest, account_id: int = None):
        data: dict = None

        try:
            if account_id and self.is_superuser_or_unauthorized():
                self.account = Account.objects.get(id=account_id)
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
            self.account.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request, account_id: int = None):
        if account_id and self.is_superuser_or_unauthorized():
            self.account = get_object_or_404(Account, pk=account_id)

        try:
            with transaction.atomic():
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
        if self.request.user.is_superuser:
            return Account.objects.all()
        return self.user_profile.account
