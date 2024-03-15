# -*- coding: utf-8 -*-
"""Billing Views for the account dashboard."""
from smarter.apps.account.views.dashboard.billing.billing_addresses import (
    BillingAddressForm,
)
from smarter.apps.account.views.dashboard.billing.payment_methods import (
    PaymentMethodForm,
)
from smarter.view_helpers import SmarterAdminWebView


# pylint: disable=W0511,C0415
class BillingView(SmarterAdminWebView):
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
        billing_address_form = BillingAddressForm()
        context = {
            "billing": {
                "payment_methods": self.payment_methods(),
                "billing_addresses": self.billing_addresses(),
                "payment_method_form": payment_method_form,
                "billing_address_form": billing_address_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)
