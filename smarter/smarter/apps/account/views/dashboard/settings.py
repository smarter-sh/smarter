"""Views for the account settings."""

import logging
import os
from http import HTTPStatus

from django import forms, http

from smarter.apps.account.models import Account, UserProfile
from smarter.lib.django.view_helpers import SmarterAdminWebView
from smarter.lib.unittest.utils import get_readonly_csv_file


logger = logging.getLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))


countries_csv = os.path.join(HERE, "./data/countries.csv")
COUNTRIES = get_readonly_csv_file(countries_csv)

languages_csv = os.path.join(HERE, "./data/languages.csv")
LANGUAGES = get_readonly_csv_file(languages_csv)

timezones_csv = os.path.join(HERE, "./data/timezones.csv")
TIMEZONES = get_readonly_csv_file(timezones_csv)

currencies_csv = os.path.join(HERE, "./data/currencies.csv")
CURRENCIES = get_readonly_csv_file(currencies_csv)


class AccountForm(forms.ModelForm):
    """Form for Account editing."""

    class Meta:
        """Meta class for AccountForm with all fields."""

        model = Account
        fields = "__all__"


class SettingsView(SmarterAdminWebView):
    """View for the account settings."""

    template_path = "account/dashboard/settings.html"

    def _exists(self, key: str, value: str, db: list) -> bool:
        for item in db:
            if item[key] == value:
                return True
        return False

    def _handle_write(self, request):
        user_profile = UserProfile.objects.get(user=request.user)
        account_form = AccountForm(request.POST, instance=user_profile.account)
        if account_form.is_valid():
            if not self._exists("value", str(account_form.instance.currency), CURRENCIES):
                return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data={"currency": "Invalid currency."})
            if not self._exists("code", str(account_form.instance.country), COUNTRIES):
                return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data={"country": "Invalid country."})
            if not self._exists("value", str(account_form.instance.language), LANGUAGES):
                return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data={"language": "Invalid language."})
            if not self._exists("value", str(account_form.instance.timezone), TIMEZONES):
                return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data={"timezone": "Invalid timezone."})

            account_form.save()
            return http.JsonResponse(status=HTTPStatus.OK, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=account_form.errors)

    # -------------------------------------------------------------------------
    # HTTP override methods
    # -------------------------------------------------------------------------
    def get(self, request):
        user_profile = UserProfile.objects.get(user=request.user)
        account_form = AccountForm(instance=user_profile.account)
        context = {
            "account_settings": {
                "account_form": account_form,
                "countries": COUNTRIES,
                "languages": LANGUAGES,
                "timezones": TIMEZONES,
                "currencies": CURRENCIES,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        return self._handle_write(request)

    def patch(self, request):
        return self._handle_write(request)

    def put(self, request):
        return self._handle_write(request)
