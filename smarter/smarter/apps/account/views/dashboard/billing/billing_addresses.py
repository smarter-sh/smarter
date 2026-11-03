# pylint: disable=W0511,W0613
"""Billing Views for the account dashboard."""

from http import HTTPStatus
from typing import Optional
from warnings import deprecated

from django import forms, http

from smarter.apps.account.tests.factories import billing_address_factory
from smarter.apps.account.views.dashboard import ACCOUNT_UI_DEPRECATION_MESSAGE
from smarter.lib.django.views import SmarterAdminWebView


class BillingAddressForm(forms.Form):
    """Form for the billing addresses modal."""

    first_name = forms.CharField()
    last_name = forms.CharField()
    address1 = forms.CharField()
    address2 = forms.CharField()
    city = forms.CharField()
    state = forms.CharField()
    zip = forms.CharField()
    country = forms.CharField()


@deprecated(ACCOUNT_UI_DEPRECATION_MESSAGE)
class BillingAddressesView(SmarterAdminWebView):
    """View for the account billing payment methods."""

    # TODO: Replace this with actual billing addresses
    def get(self, request):
        """
        Return three randomly generated billing addresses, a placeholder until billing exists.

        :param request: The request.
        :returns: A json response.
        """
        retval = [billing_address_factory(), billing_address_factory(), billing_address_factory()]
        return http.JsonResponse(data=retval, safe=False, status=HTTPStatus.OK.value)


@deprecated(ACCOUNT_UI_DEPRECATION_MESSAGE)
class BillingAddressView(SmarterAdminWebView):
    """View for the account billing detail payment method."""

    # pylint: disable=W0612
    def process_form(self, request):
        """
        Validate the billing address form.

        Nothing is saved yet.

        :param request: The request, with the form's data.
        :returns: A json response: 200 when the form is valid, else 400.
        """
        # TODO: Add payment method to user's account
        form = BillingAddressForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            address1 = form.cleaned_data["address1"]
            address2 = form.cleaned_data["address2"]
            city = form.cleaned_data["city"]
            state = form.cleaned_data["state"]
            postcode = form.cleaned_data["zip"]
            country = form.cleaned_data["country"]
            return http.JsonResponse(status=HTTPStatus.OK.value, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data={})

    # pylint: disable=W0221
    def get(self, request, billing_address_id: str):
        """
        Return a randomly generated billing address, a placeholder until billing exists.

        :param request: The request.
        :param billing_address_id: Unused.
        :returns: A json response.
        """
        retval = billing_address_factory()
        return http.JsonResponse(data=retval, safe=False, status=HTTPStatus.OK.value)

    def post(self, request, billing_address_id: Optional[str] = None):
        """
        Validate the billing address form, with :meth:`process_form`.

        :param request: The request.
        :param billing_address_id: Unused.
        :returns: A json response.
        """
        return self.process_form(request)

    def patch(self, request, billing_address_id: Optional[str] = None):
        """
        Validate the billing address form, with :meth:`process_form`.

        :param request: The request.
        :param billing_address_id: Unused.
        :returns: A json response.
        """
        return self.process_form(request)

    def put(self, request, billing_address_id: Optional[str] = None):
        """
        Validate the billing address form, with :meth:`process_form`.

        :param request: The request.
        :param billing_address_id: Unused.
        :returns: A json response.
        """
        return self.process_form(request)

    def delete(self, request, billing_address_id: str):
        """
        Accept the deletion of a billing address.

        Nothing is deleted yet.

        :param request: The request.
        :param billing_address_id: Unused.
        :returns: A 200 json response.
        """
        return http.JsonResponse(data={}, status=HTTPStatus.OK.value)
