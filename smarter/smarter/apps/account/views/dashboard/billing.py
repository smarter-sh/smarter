# -*- coding: utf-8 -*-
"""Billing Views for the account dashboard."""
from http import HTTPStatus

from django import forms, http

from smarter.view_helpers import SmarterAuthenticatedWebView


class PaymentMethodForm(forms.Form):
    """Form for Payment methods modal."""

    card_name = forms.CharField()
    card_number = forms.CharField()
    card_expiry_month = forms.IntegerField()
    card_expiry_year = forms.IntegerField()
    card_cvc = forms.IntegerField()


class BillingAddressesForm(forms.Form):
    """Form for the billing addresses modal."""

    first_name = forms.CharField()
    last_name = forms.CharField()
    address1 = forms.CharField()
    address2 = forms.CharField()
    city = forms.CharField()
    state = forms.CharField()
    zip = forms.CharField()
    country = forms.CharField()


# pylint: disable=W0511,C0415
class BillingView(SmarterAuthenticatedWebView):
    """View for the account billing."""

    template_path = "account/dashboard/billing.html"

    # TODO: Replace this with actual billing addresses
    def billing_addresses(self):
        def billing_address():
            import uuid

            return {
                "id": str(uuid.uuid4()),
                "is_primary": True,
                "address1": "123 Main St",
                "address2": "Apt 123",
                "city": "Anytown",
                "state": "CA",
                "zip": "12345",
                "country": "US",
            }

        return [billing_address(), billing_address(), billing_address()]

    # TODO: Replace this with actual payment methods
    # pylint: disable=C0415
    def payment_methods(self):
        """View for the payment methods."""

        def payment_method():
            import random
            import uuid

            return {
                "id": str(uuid.uuid4()),
                "is_primary": True,
                "owner": "John Doe",
                "type": random.choice(["visa", "mastercard", "american-express"]),
                "description": "Visa ending in " + str(random.randint(1000, 9999)),
                "expiration": "12/2027",
            }

        return [payment_method(), payment_method(), payment_method()]

    def get(self, request):
        payment_method_form = PaymentMethodForm()
        billing_address_form = BillingAddressesForm()
        context = {
            "billing": {
                "payment_methods": self.payment_methods(),
                "billing_addresses": self.billing_addresses(),
                "payment_method_form": payment_method_form,
                "billing_address_form": billing_address_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class PaymentMethodsView(SmarterAuthenticatedWebView):
    """View for the account billing payment methods."""

    # pylint: disable=W0612
    def process_form(self, request):
        # TODO: Add payment method to user's account
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            card_name = form.cleaned_data["card_name"]
            card_number = form.cleaned_data["card_number"]
            card_expiry_month = form.cleaned_data["card_expiry_month"]
            card_expiry_year = form.cleaned_data["card_expiry_year"]
            card_cvc = form.cleaned_data["card_cvc"]
            return http.JsonResponse(status=HTTPStatus.OK, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data={})

    def post(self, request):
        self.process_form(request)

    def patch(self, request):
        self.process_form(request)

    def put(self, request):
        self.process_form(request)


class BillingAddressesView(SmarterAuthenticatedWebView):
    """View for the account billing payment methods."""

    # pylint: disable=W0612
    def process_form(self, request):
        # TODO: Add payment method to user's account
        form = BillingAddressesForm(request.POST)
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

    def post(self, request):
        self.process_form(request)

    def patch(self, request):
        self.process_form(request)

    def put(self, request):
        self.process_form(request)
