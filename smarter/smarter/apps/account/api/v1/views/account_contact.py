# pylint: disable=W0707,W0718
"""AccountContact views for smarter api."""

from http import HTTPStatus
from typing import Optional

from django.db import transaction
from django.http import (
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

from smarter.apps.account.contract.models import AccountApiContact
from smarter.apps.account.models import AccountContact
from smarter.apps.account.serializers import AccountContactSerializer
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


# pylint: disable=W0613
class AccountContactView(AccountViewBase):
    """AccountContact view for smarter api.

    Its ``GET`` returns an :class:`AccountApiContact`.
    """

    serializer_class = AccountContactSerializer
    account_contact: AccountContact

    def get(self, request: Request, account_contact_id: int):
        self.account_contact = get_object_or_404(
            AccountContact.objects.select_related("account"), pk=account_contact_id
        )
        return JsonResponse(AccountApiContact.from_model(self.account_contact).model_dump(mode="json"))

    def post(self, request: Request):
        return HttpResponseBadRequest()

    def patch(self, request: Request, account_contact_id: Optional[int] = None):
        return HttpResponseBadRequest()

    def delete(self, request, account_contact_id: int):
        self.account_contact = get_object_or_404(AccountContact, pk=account_contact_id)

        try:
            with transaction.atomic():
                if not isinstance(self.account_contact, AccountContact):
                    return JsonResponse({"error": "AccountContact not found"}, status=HTTPStatus.NOT_FOUND)
                self.account_contact.delete()
                AccountContact.objects.get(user=request.user).delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class AccountContactListView(ContractListMixin, AccountListViewBase):
    """AccountContact list view for smarter api: :class:`AccountApiContact` models."""

    serializer_class = AccountContactSerializer
    contract_model = AccountApiContact

    def get_queryset(self):
        if not self.request:
            return AccountContact.objects.none()
        if not self.request.user.is_authenticated:  # type: ignore
            return AccountContact.objects.none()
        contacts = AccountContact.objects.select_related("account").order_by("pk")
        if self.request.user.is_superuser:  # type: ignore
            return contacts
        return contacts.filter(account=self.user_profile.account)  # type: ignore
