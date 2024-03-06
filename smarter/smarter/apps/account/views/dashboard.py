# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django views for the account dashboard."""

from smarter.view_helpers import SmarterAuthenticatedWebView


class OverviewView(SmarterAuthenticatedWebView):
    """View for the account dashboard."""

    template_path = "account/dashboard/overview.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class SettingsView(SmarterAuthenticatedWebView):
    """View for the account settings."""

    template_path = "account/dashboard/settings.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class ActivityView(SmarterAuthenticatedWebView):
    """View for the account activity."""

    template_path = "account/dashboard/activity.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class BillingView(SmarterAuthenticatedWebView):
    """View for the account billing."""

    template_path = "account/dashboard/billing.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class StatementsView(SmarterAuthenticatedWebView):
    """View for the account statements."""

    template_path = "account/dashboard/statements.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class APIKeysView(SmarterAuthenticatedWebView):
    """View for the account API keys."""

    template_path = "account/dashboard/api-keys.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class LogsView(SmarterAuthenticatedWebView):
    """View for the account logs."""

    template_path = "account/dashboard/logs.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class CardDeclinedView(SmarterAuthenticatedWebView):
    """View for the card declined page."""

    template_path = "account/dashboard/card-declined.html"

    def get(self, request):
        # FIX NOTE: This is a temporary solution to display the card declined page.
        context = {
            "card_declined": {
                "customer_name": "John Doe",
                "account_number": "1234567890",
                "card_number": "1234",
                "transaction_date": "01/01/2020",
                "transaction_amount": "$100.00",
                "phone_number": "+1 (512) 833-6955",
                "contact_url": "https://www.querium.com/contact/",
                "main_url": "https://www.querium.com/",
                "support_email": "support“querium.com",
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)
