# pylint: disable=W0707,W0718
"""AccountContact views for smarter api."""

from http import HTTPStatus
from typing import Optional

from django.db import transaction
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

from smarter.apps.account.models import AccountContact
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


# pylint: disable=W0613
class AccountContactView(AccountViewBase):
    """AccountContact view for smarter api."""

    account_contact: AccountContact

    def get(self, request: Request, account_contact_id: int):
        if account_contact_id and request.user.is_superuser:  # type: ignore
            self.account_contact = get_object_or_404(AccountContact, pk=account_contact_id)
        else:
            return Http404()

    def post(self, request: Request):
        return HttpResponseBadRequest()

    def patch(self, request: Request, account_contact_id: Optional[int] = None):
        return HttpResponseBadRequest()

    def delete(self, request, account_contact_id: int):
        if account_contact_id and self.is_superuser_or_unauthorized():
            self.account_contact = get_object_or_404(AccountContact, pk=account_contact_id)
        else:
            return HttpResponseForbidden()

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


class AccountContactListView(AccountListViewBase):
    """AccountContact list view for smarter api."""

    account_contact: AccountContact

    def get_queryset(self):
        if not isinstance(self.account_contact, AccountContact):
            return AccountContact.objects.none()
        if not self.request:
            return AccountContact.objects.none()
        if not self.request.user.is_authenticated:  # type: ignore
            return AccountContact.objects.none()
        if self.request.user.is_superuser:  # type: ignore
            return AccountContact.objects.all()
        return self.account_contact
