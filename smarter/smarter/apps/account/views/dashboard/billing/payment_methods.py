# -*- coding: utf-8 -*-
# pylint: disable=W0511
"""Billing Views for the account dashboard."""
from http import HTTPStatus

from django import forms, http

from smarter.view_helpers import SmarterAdminWebView


class PaymentMethodForm(forms.Form):
    """Form for Payment methods modal."""

    card_name = forms.CharField()
    card_number = forms.CharField()
    card_expiry_month = forms.IntegerField()
    card_expiry_year = forms.IntegerField()
    card_cvc = forms.IntegerField()


class PaymentMethodsView(SmarterAdminWebView):
    """View for the account billing payment methods listview."""

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


class PaymentMethodView(SmarterAdminWebView):
    """View for the account billing detail payment method."""
