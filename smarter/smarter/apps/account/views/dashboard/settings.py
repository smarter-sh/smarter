# -*- coding: utf-8 -*-
"""Views for the account settings."""
import csv
import logging
import os
from http import HTTPStatus

from django import forms, http

from smarter.common.view_helpers import SmarterAdminWebView

from ...models import Account, UserProfile


logger = logging.getLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))


def get_from_csv(file_path):
    """Reads a CSV file and returns a list of dictionaries."""
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


countries_csv = os.path.join(HERE, "./data/countries.csv")
COUNTRIES = get_from_csv(countries_csv)

languages_csv = os.path.join(HERE, "./data/languages.csv")
LANGUAGES = get_from_csv(languages_csv)

timezones_csv = os.path.join(HERE, "./data/timezones.csv")
TIMEZONES = get_from_csv(timezones_csv)

currencies_csv = os.path.join(HERE, "./data/currencies.csv")
CURRENCIES = get_from_csv(currencies_csv)


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
