# -*- coding: utf-8 -*-
# pylint: disable=W0511,W0613
"""Billing Views for the account dashboard."""
from http import HTTPStatus

from django import forms, http

from smarter.smarter.common.view_helpers import SmarterAdminWebView

from ....tests.factories import billing_address_factory


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


class BillingAddressesView(SmarterAdminWebView):
    """View for the account billing payment methods."""

    # TODO: Replace this with actual billing addresses
    def get(self, request):
        retval = [billing_address_factory(), billing_address_factory(), billing_address_factory()]
        return http.JsonResponse(data=retval, safe=False, status=HTTPStatus.OK)


class BillingAddressView(SmarterAdminWebView):
    """View for the account billing detail payment method."""

    # pylint: disable=W0612
    def process_form(self, request):
        # TODO: Add payment method to user's account
        form = BillingAddressForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            address1 = form.cleaned_data["address1"]
            address2 = form.cleaned_data["address2"]
            city = form.cleaned_data["city"]
            state = form.cleaned_data["state"]
            postcode = form.cleaned_data["postcode"]
            country = form.cleaned_data["country"]
            return http.JsonResponse(status=HTTPStatus.OK, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data={})

    # pylint: disable=W0221
    def get(self, request, billing_address_id: str):
        """View for the payment method."""
        retval = billing_address_factory()
        return http.JsonResponse(data=retval, safe=False, status=HTTPStatus.OK)

    def post(self, request, billing_address_id: str = None):
        self.process_form(request)

    def patch(self, request, billing_address_id: str = None):
        self.process_form(request)

    def put(self, request, billing_address_id: str = None):
        self.process_form(request)

    def delete(self, request, billing_address_id: str):
        return http.JsonResponse(data={}, status=HTTPStatus.OK)
