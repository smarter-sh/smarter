# -*- coding: utf-8 -*-
"""Billing Views for the account dashboard."""
import csv
import datetime
import json
import logging
import os
from pathlib import Path

from smarter.smarter.common.view_helpers import SmarterAdminWebView

from .billing_addresses import BillingAddressesView, BillingAddressForm
from .payment_methods import PaymentMethodForm, PaymentMethodsView


logger = logging.getLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))
DASHBOARD = str(Path(HERE).parent)


def get_from_csv(file_path):
    """Reads a CSV file and returns a list of dictionaries."""
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


countries_csv = os.path.join(DASHBOARD, "./data/countries.csv")
COUNTRIES = get_from_csv(countries_csv)


# pylint: disable=W0511,C0415
class BillingView(SmarterAdminWebView):
    """View for the account billing."""

    template_path = "account/dashboard/billing.html"

    def get(self, request):
        """
        Composite View for account billing, including JSON data for
        payment methods and billing addresses.
        """
        payment_method_form = PaymentMethodForm()
        billing_address_form = BillingAddressForm()
        billing_addresses_view = BillingAddressesView().get(request)
        billing_addresses = json.loads(billing_addresses_view.content)
        payment_methods_view = PaymentMethodsView().get(request)
        payment_methods = json.loads(payment_methods_view.content)
        current_year = datetime.datetime.now().year
        payment_method_expiration_years = list(range(current_year, current_year + 7))
        context = {
            "billing": {
                "payment_methods": payment_methods,
                "billing_addresses": billing_addresses,
                "payment_method_form": payment_method_form,
                "billing_address_form": billing_address_form,
                "payment_method_expiration_years": payment_method_expiration_years,
                "countries": COUNTRIES,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)
