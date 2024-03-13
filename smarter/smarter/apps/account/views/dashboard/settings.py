# -*- coding: utf-8 -*-
"""Views for the account settings."""
import csv
import logging
import os
from http import HTTPStatus

from django import forms, http

from smarter.apps.account.models import Account, UserProfile
from smarter.view_helpers import SmarterAuthenticatedWebView


logger = logging.getLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))

# Open and read the CSV file
countries_csv = os.path.join(HERE, "./data/countries.csv")
with open(countries_csv, mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    COUNTRIES = list(reader)

languages_csv = os.path.join(HERE, "./data/languages.csv")
with open(languages_csv, mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    LANGUAGES = list(reader)

timezones_csv = os.path.join(HERE, "./data/timezones.csv")
with open(timezones_csv, mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    TIMEZONES = list(reader)

currencies_csv = os.path.join(HERE, "./data/currencies.csv")
with open(currencies_csv, mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    CURRENCIES = list(reader)


class AccountForm(forms.ModelForm):
    """Form for Payment methods modal."""

    class Meta:
        """Meta class for AccountForm with all fields."""

        model = Account
        fields = "__all__"


class SettingsView(SmarterAuthenticatedWebView):
    """View for the account settings."""

    template_path = "account/dashboard/settings.html"

    def get(self, request):
        logger.info("Handling get request w %s languages", len(LANGUAGES))
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

    def _handle_write(self, request):
        logger.info("Handling write request: %s", request.POST)
        user_profile = UserProfile.objects.get(user=request.user)
        account_form = AccountForm(request.POST, instance=user_profile.account)
        if account_form.is_valid():
            account_form.save()
            return http.JsonResponse(status=HTTPStatus.OK, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=account_form.errors)

    def post(self, request):
        return self._handle_write(request)

    def patch(self, request):
        return self._handle_write(request)

    def put(self, request):
        return self._handle_write(request)
