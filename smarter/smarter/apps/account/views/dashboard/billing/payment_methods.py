# pylint: disable=W0511,W0613
"""Billing Views for the account dashboard."""
import logging
from http import HTTPStatus

from django import forms, http

from smarter.apps.account.tests.factories import payment_method_factory
from smarter.lib.django.view_helpers import SmarterAdminWebView


logger = logging.getLogger(__name__)


class PaymentMethodForm(forms.Form):
    """Form for Payment methods modal."""

    id = forms.UUIDField()
    is_primary = forms.BooleanField()
    card_type = forms.CharField()
    card_name = forms.CharField()
    card_number = forms.CharField()
    card_expiration_month = forms.IntegerField()
    card_expiration_year = forms.IntegerField()
    card_cvc = forms.IntegerField()


class PaymentMethodsView(SmarterAdminWebView):
    """View for the account billing payment methods listview."""

    # TODO: Replace this with actual payment methods
    # pylint: disable=C0415
    def get(self, request):
        """View for the payment methods."""

        retval = [payment_method_factory(), payment_method_factory(), payment_method_factory()]
        return http.JsonResponse(data=retval, safe=False, status=HTTPStatus.OK.value)


class PaymentMethodView(SmarterAdminWebView):
    """View for the account billing detail payment method."""

    # pylint: disable=W0612
    def process_form(self, request):
        # TODO: Add payment method to user's account
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            # id = form.cleaned_data["id"]
            # is_primary = form.cleaned_data["is_primary"]
            # card_name = form.cleaned_data["card_name"]
            # card_number = form.cleaned_data["card_number"]
            # card_expiration_month = form.cleaned_data["card_expiration_month"]
            # card_expiry_year = form.cleaned_data["card_expiry_year"]
            # card_cvc = form.cleaned_data["card_cvc"]
            return http.JsonResponse(status=HTTPStatus.OK.value, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data={})

    # pylint: disable=W0221
    def get(self, request, payment_method_id: str):
        """View for the payment method detail."""
        retval = payment_method_factory()
        return http.JsonResponse(data=retval, safe=False, status=HTTPStatus.OK.value)

    def post(self, request, payment_method_id: str = None):
        return self.process_form(request)

    def patch(self, request, payment_method_id: str = None):
        return self.process_form(request)

    def put(self, request, payment_method_id: str = None):
        return self.process_form(request)

    def delete(self, request, payment_method_id: str):
        logger.info("Deleting payment method %s", payment_method_id)
        return http.JsonResponse(data={}, status=HTTPStatus.OK.value)
