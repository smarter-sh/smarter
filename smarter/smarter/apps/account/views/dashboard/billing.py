# -*- coding: utf-8 -*-
"""Billing Views for the account dashboard."""
from smarter.view_helpers import SmarterAuthenticatedWebView


class BillingView(SmarterAuthenticatedWebView):
    """View for the account billing."""

    template_path = "account/dashboard/billing.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)
