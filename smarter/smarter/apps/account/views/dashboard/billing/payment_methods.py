# pylint: disable=W0511,W0613
"""Billing Views for the account dashboard."""
import logging
import random
import uuid
from datetime import datetime
from http import HTTPStatus

from django import forms, http

from smarter.lib.django.view_helpers import SmarterAdminWebView


logger = logging.getLogger(__name__)


def payment_method_factory():

    def generate_card_number(card_type: str = "visa"):
        if card_type == "visa":
            return "4" + "".join(random.choices("0123456789", k=15))
        if card_type == "mastercard":
            return "5" + "".join(random.choices("0123456789", k=15))
        if card_type == "american-express":
            return "3" + "".join(random.choices("0123456789", k=14))
        return "-".join(["".join(random.choices("0123456789", k=4)) for _ in range(4)])

    def mask_card(card_number):
        return "ending " + str(card_number)[-4:]

    card_type = random.choice(["visa", "mastercard", "american-express"])
    card_number = generate_card_number(card_type)
    card_masked = mask_card(card_number)
    return {
        "id": str(uuid.uuid4()),
        "is_primary": True,
        "card_type": card_type,
        "card_name": "John Doe",
        "card_number": card_number,
        "card_masked": card_masked,
        "card_expiration_month": 12,
        "card_expiration_year": random.randint(datetime.now().year, datetime.now().year + 7),
        "card_cvc": random.randint(100, 999),
    }


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
