# -*- coding: utf-8 -*-
"""Billing Views for the account dashboard."""
from smarter.view_helpers import SmarterAuthenticatedWebView


# pylint: disable=W0511
class BillingView(SmarterAuthenticatedWebView):
    """View for the account billing."""

    template_path = "account/dashboard/billing.html"

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
        context = {
            "billing": {
                "payment_methods": self.payment_methods(),
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)
