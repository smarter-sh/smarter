# pylint: disable=W0707,W0718
"""Account views for smarter api."""

from http import HTTPStatus
from typing import Optional

from django.http import (
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.contract.models import AccountApiAccountDetail
from smarter.apps.account.models import Account, UserProfile
from smarter.common.utils import to_snake_case
from smarter.lib import json, logging
from smarter.lib.django.http.client_errors import (
    CLIENT_ERROR_TYPES,
    REQUEST_DATA_ERROR_TYPES,
    client_error_message,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.typing import SmarterDictType

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class AccountView(AccountViewBase):
    """Account view for smarter api.

    Its ``GET`` returns an :class:`AccountApiAccountDetail`.
    """

    def get(self, request: Request, account_id: int):
        """
        Return an Account as json.

        :param request: The request.
        :param account_id: The Account's id. Only a superuser may read another Account; anyone else gets
            the Account of their own UserProfile.
        :returns: The :class:`AccountApiAccountDetail` of the Account.
        :raises PermissionDenied: when a non-superuser has no UserProfile.
        """
        logger.debug("called with account_id: %s", account_id)
        if account_id and request.user.is_superuser:  # type: ignore
            account = get_object_or_404(Account, pk=account_id)
        else:
            if not isinstance(self.user_profile, UserProfile):
                raise PermissionDenied("User profile not found")
            account = self.user_profile.account
        return Response(AccountApiAccountDetail.from_model(account).model_dump(mode="json"), status=HTTPStatus.OK)

    # pylint: disable=W0613
    def post(self, request: Request, account_id: Optional[int] = None):
        """
        Create an Account from the json dict in the request body.

        :param request: The request, whose body holds the Account's fields.
        :param account_id: Unused.
        :returns: A redirect to the new Account's url, or a 400 response when the body is not a json
            dict or the Account cannot be created.
        """
        logger.debug("called with data: %s", request.data)
        try:
            data = request.data
            if not isinstance(data, dict):
                raise json.JSONDecodeError(
                    f"Expected a JSON dict in request body but received {type(data)}", doc=str(data), pos=0
                )
            logger.debug("parsed JSON data: %s", data)
        except json.JSONDecodeError as e:
            logger.error("JSON decode error: %s", str(e))
            return HttpResponseBadRequest(f"Invalid JSON data: {str(e)}")

        try:
            name = data.get("name", data.get("account_number", "company_name")) or "Default_Account_Name"
            data["name"] = to_snake_case(name)
            account = Account.objects.create(**data)
        except REQUEST_DATA_ERROR_TYPES as e:
            logger.warning("could not create the account: %s", type(e).__name__)
            message = client_error_message(e, "The Account could not be created.")
            return HttpResponseBadRequest(f"Invalid request data: {message}")
        # pylint: disable=broad-except
        except Exception:
            logger.error("error creating account", exc_info=True)
            return HttpResponseServerError("An unknown error occurred while creating the Account.")

        return HttpResponseRedirect(request.path_info + str(account.id) + "/")  # type: ignore

    def patch(self, request: Request, account_id: int):
        """
        Update an Account's fields from the json dict in the request body, and save it.

        Keys that are not attributes of the Account are ignored.

        :param request: The request, whose body holds the fields to change.
        :param account_id: The Account's id.
        :returns: The response: 404 when the Account does not exist, 400 when the body or the new values
            are not valid.
        """
        logger.debug("called for account_id: %s", account_id)
        account: Account

        if not isinstance(request.data, dict):
            return HttpResponseBadRequest(
                f"Invalid request data. Expected a JSON dict in request body but received {type(request.data)}"
            )

        try:
            account = Account.get_cached_object(pk=account_id)
            if not isinstance(account, Account):
                raise Account.DoesNotExist(f"Account with id {account_id} does not exist.")
            logger.debug("retrieved account: %s", account)
        except Account.DoesNotExist:
            logger.debug("account with id %s not found", account_id)
            return HttpResponseNotFound("Account not found")

        # the body was parsed, and found to be a dict, above.
        data: SmarterDictType = request.data
        logger.debug("received data: %s", data)

        try:
            for key, value in data.items():
                if hasattr(account, key):
                    setattr(account, key, value)
            account.save()  # type: ignore
            logger.debug("updated account: %s", account)
        except CLIENT_ERROR_TYPES as e:
            logger.warning("could not update the account: %s", type(e).__name__)
            message = client_error_message(e, "The Account could not be updated.")
            return HttpResponseBadRequest(message)
        # pylint: disable=broad-except
        except Exception:
            logger.error("internal error updating account", exc_info=True)
            return HttpResponseServerError("An unknown error occurred while updating the Account.")

        return HttpResponseRedirect(request.path_info)

    def delete(self, request, account_id: int):
        """
        Delete an Account.

        :param request: The request.
        :param account_id: The Account's id.
        :returns: A redirect to ``/``, or a 500 response when the delete fails.
        :raises Http404: when the Account does not exist.
        """
        logger.debug("called with account_id: %s", account_id)
        account: Account
        account = get_object_or_404(Account, pk=account_id)
        logger.debug("retrieved account: %s", account)

        try:
            account.delete()
        except CLIENT_ERROR_TYPES as e:
            logger.warning("refused: %s", type(e).__name__)
            message = client_error_message(e, "The Account could not be deleted.")
            return HttpResponseBadRequest(message)
        # pylint: disable=broad-except
        except Exception:
            logger.error("internal error deleting account", exc_info=True)
            return HttpResponseServerError("An unknown error occurred while deleting the Account.")

        return HttpResponseRedirect("/")


class AccountListView(ContractListMixin, AccountListViewBase):
    """Account list view for smarter api: :class:`AccountApiAccountDetail` models."""

    contract_model = AccountApiAccountDetail

    def get_queryset(self):
        """
        Return every Account for a superuser, and none for anyone else.

        :returns: The queryset.
        """
        logger.debug("called")
        if self.is_superuser():
            return Account.objects.all()
        return Account.objects.none()
