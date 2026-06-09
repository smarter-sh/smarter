# pylint: disable=W0707,W0718
"""Account views for smarter api."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile
from smarter.common.utils import to_snake_case
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class AccountView(AccountViewBase):
    """Account view for smarter api."""

    def get(self, request: Request, account_id: int):
        logger.debug("%s.get() called with account_id: %s", self.formatted_class_name, account_id)
        if account_id and request.user.is_superuser:  # type: ignore
            account = get_object_or_404(Account, pk=account_id)
        else:
            if not isinstance(self.user_profile, UserProfile):
                return HttpResponseForbidden("User profile not found")
            account = self.user_profile.account
        serializer = self.serializer_class(account)
        return Response(serializer.data, status=HTTPStatus.OK)

    # pylint: disable=W0613
    def post(self, request: Request, account_id: Optional[int] = None):
        logger.debug("%s.post() called with data: %s", self.formatted_class_name, request.data)
        try:
            data = request.data
            if not isinstance(data, dict):
                raise json.JSONDecodeError(
                    f"Expected a JSON dict in request body but received {type(data)}", doc=str(data), pos=0
                )
            logger.debug("%s.post() parsed JSON data: %s", self.formatted_class_name, data)
        except json.JSONDecodeError as e:
            logger.error("%s.post() JSON decode error: %s", self.formatted_class_name, str(e))
            return HttpResponseBadRequest(f"Invalid JSON data: {str(e)}")

        try:
            name = data.get("name", data.get("account_number", "company_name")) or "Default_Account_Name"
            data["name"] = to_snake_case(name)
            account = Account.objects.create(**data)
        except Exception as e:
            logger.error("%s.post() error creating account: %s", self.formatted_class_name, str(e), exc_info=True)
            return HttpResponseBadRequest(f"Invalid request data: {str(e)}")

        return HttpResponseRedirect(request.path_info + str(account.id) + "/")  # type: ignore

    def patch(self, request: Request, account_id: int):
        logger.debug("%s.patch() called for account_id: %s", self.formatted_class_name, account_id)
        account: Account

        if not isinstance(request.data, dict):
            return HttpResponseBadRequest(
                f"Invalid request data. Expected a JSON dict in request body but received {type(request.data)}"
            )

        try:
            account = Account.get_cached_object(pk=account_id)
            if not isinstance(account, Account):
                raise Account.DoesNotExist(f"Account with id {account_id} does not exist.")
            logger.debug("%s.patch() retrieved account: %s", self.formatted_class_name, account)
        except Account.DoesNotExist:
            logger.debug("%s.patch() account with id %s not found", self.formatted_class_name, account_id)
            return HttpResponseNotFound("Account not found")

        try:
            data: dict = request.data
            if not isinstance(data, dict):
                return HttpResponseBadRequest(
                    f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"
                )
            logger.debug("%s.patch() received data: %s", self.formatted_class_name, data)
        except Exception as e:
            logger.error("%s.patch() error parsing request data: %s", self.formatted_class_name, str(e))
            return HttpResponseBadRequest(f"Invalid request data: {str(e)}")

        try:
            for key, value in data.items():
                if hasattr(account, key):
                    setattr(account, key, value)
            account.save()  # type: ignore
            logger.debug("%s.patch() updated account: %s", self.formatted_class_name, account)
        except ValidationError as e:
            logger.error(
                "%s.patch() validation error updating account: %s", self.formatted_class_name, str(e), exc_info=True
            )
            return HttpResponseBadRequest(e.message)
        except Exception as e:
            logger.error(
                "%s.patch() internal error updating account: %s", self.formatted_class_name, str(e), exc_info=True
            )
            return HttpResponseServerError(f"Internal error: {str(e)}")

        return HttpResponseRedirect(request.path_info)

    def delete(self, request, account_id: int):
        logger.debug("%s.delete() called with account_id: %s", self.formatted_class_name, account_id)
        account: Account
        account = get_object_or_404(Account, pk=account_id)
        logger.debug("%s.delete() retrieved account: %s", self.formatted_class_name, account)

        try:
            account.delete()
        except Exception as e:
            logger.error(
                "%s.delete() internal error deleting account: %s", self.formatted_class_name, str(e), exc_info=True
            )
            return HttpResponseServerError(f"Internal error: {str(e)}")

        return HttpResponseRedirect("/")


class AccountListView(AccountListViewBase):
    """Account list view for smarter api."""

    def get_queryset(self):
        logger.debug("%s.get_queryset() called", self.formatted_class_name)
        if self.is_superuser():
            return Account.objects.all()
        return Account.objects.none()
