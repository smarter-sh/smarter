# pylint: disable=W0707,W0718
"""AccountContact views for smarter api."""

from http import HTTPStatus
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet
from django.http import (
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

from smarter.apps.account.contract.models import AccountApiContact
from smarter.apps.account.models import AccountContact, UserProfile
from smarter.apps.account.serializers import AccountContactSerializer
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin

from .base import AccountListViewBase, AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def readable_contacts(request: Optional[Request], user_profile: Optional[UserProfile]) -> QuerySet[AccountContact]:
    """
    Return the AccountContacts that the request's user may see and change.

    A superuser may see every AccountContact, anyone else only those of their own account.

    :param request: The request.
    :param user_profile: The request user's profile.
    :returns: The AccountContacts, ordered by pk; none for an anonymous request.
    """
    if request is None:
        return AccountContact.objects.none()
    user = request.user
    if not user.is_authenticated:
        return AccountContact.objects.none()
    contacts = AccountContact.objects.select_related("account").order_by("pk")
    if user.is_superuser:
        return contacts
    if user_profile is None:
        return AccountContact.objects.none()
    account_contacts = contacts.filter(account=user_profile.account)
    return account_contacts


# pylint: disable=W0613
class AccountContactView(AccountViewBase):
    """AccountContact view for smarter api.

    Its ``GET`` returns an :class:`AccountApiContact`.
    """

    serializer_class = AccountContactSerializer
    account_contact: AccountContact

    def get(self, request: Request, account_contact_id: int):
        """
        Return an AccountContact as json.

        :param request: The request.
        :param account_contact_id: The AccountContact's id.
        :returns: The :class:`AccountApiContact` of the AccountContact.
        :raises Http404: when the AccountContact does not exist, or is another account's.
        """
        contacts = readable_contacts(request, self.user_profile)
        self.account_contact = get_object_or_404(contacts, pk=account_contact_id)
        return JsonResponse(AccountApiContact.from_model(self.account_contact).model_dump(mode="json"))

    def post(self, request: Request):
        """
        Refuse to create an AccountContact: this endpoint does not support it.

        :param request: The request.
        :returns: A 400 response.
        """
        return HttpResponseBadRequest()

    def patch(self, request: Request, account_contact_id: Optional[int] = None):
        """
        Refuse to update an AccountContact: this endpoint does not support it.

        :param request: The request.
        :param account_contact_id: Unused.
        :returns: A 400 response.
        """
        return HttpResponseBadRequest()

    def delete(self, request, account_contact_id: int):
        """
        Delete an AccountContact, and the AccountContact of the request user, in one transaction.

        The request user's AccountContact is the one in the same account with the user's email.
        When there is none, nothing is deleted.

        :param request: The request.
        :param account_contact_id: The AccountContact's id.
        :returns: A redirect to the parent url, a 404 response when the request user has no
            AccountContact in the account, or a 500 response when the delete fails.
        :raises Http404: when the AccountContact does not exist, or is another account's.
        """
        contacts = readable_contacts(request, self.user_profile)
        self.account_contact = get_object_or_404(contacts, pk=account_contact_id)
        user_email = getattr(request.user, "email", None)

        try:
            with transaction.atomic():
                user_contact = AccountContact.objects.filter(
                    account=self.account_contact.account, email=user_email
                ).first()
                if user_contact is None:
                    return JsonResponse(
                        {"error": "The request user has no AccountContact in this account."},
                        status=HTTPStatus.NOT_FOUND,
                    )
                # delete() clears the pk, so compare the rows first.
                same_contact = user_contact.pk == self.account_contact.pk
                self.account_contact.delete()
                if not same_contact:
                    user_contact.delete()
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
        """
        Return every AccountContact for a superuser, else those of the user's Account.

        :returns: The queryset, ordered by pk; empty for an anonymous request.
        """
        contacts = readable_contacts(self.request, self.user_profile)
        return contacts
