# pylint: disable=W0613
"""Django views for the account dashboard."""

from warnings import deprecated

from smarter.apps.account.views.dashboard import ACCOUNT_UI_DEPRECATION_MESSAGE
from smarter.lib.django.views import SmarterAuthenticatedWebView


@deprecated(ACCOUNT_UI_DEPRECATION_MESSAGE)
class OverviewView(SmarterAuthenticatedWebView):
    """View for the account dashboard."""

    template_path = "account/dashboard/overview.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


@deprecated(ACCOUNT_UI_DEPRECATION_MESSAGE)
class ActivityView(SmarterAuthenticatedWebView):
    """View for the account activity."""

    template_path = "account/dashboard/activity.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


@deprecated(ACCOUNT_UI_DEPRECATION_MESSAGE)
class StatementsView(SmarterAuthenticatedWebView):
    """View for the account statements."""

    template_path = "account/dashboard/statements.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


@deprecated(ACCOUNT_UI_DEPRECATION_MESSAGE)
class LogsView(SmarterAuthenticatedWebView):
    """View for the account logs."""

    template_path = "account/dashboard/logs.html"

    def get(self, request):
        context = {}
        return self.clean_http_response(request, template_path=self.template_path, context=context)
