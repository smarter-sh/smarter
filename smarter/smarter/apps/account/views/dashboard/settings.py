# -*- coding: utf-8 -*-
"""Views for the account settings."""
from http import HTTPStatus

from django import forms, http

from smarter.view_helpers import SmarterAuthenticatedWebView


class ProfileForm(forms.Form):
    """Form for Payment methods modal."""

    account_number = forms.CharField()
    company_name = forms.CharField()
    address1 = forms.CharField()
    address2 = forms.CharField()
    city = forms.CharField()
    state = forms.CharField()
    postal_code = forms.CharField()
    country = forms.CharField()
    phone = forms.CharField()
    language = forms.CharField()
    timezone = forms.CharField()
    currency = forms.CharField()


class SettingsView(SmarterAuthenticatedWebView):
    """View for the account settings."""

    template_path = "account/dashboard/settings.html"

    def get(self, request):
        profile_form = ProfileForm()
        context = {
            "account_settings": {
                "profile_form": profile_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class ProfileView(SmarterAuthenticatedWebView):
    """View for the account billing payment methods."""

    # pylint: disable=W0612,W0511
    def process_form(self, request):
        # TODO: persist this
        form = ProfileForm(request.POST)
        if form.is_valid():
            account_number = form.cleaned_data["account_number"]
            company_name = form.cleaned_data["company_name"]
            address1 = form.cleaned_data["address1"]
            address2 = form.cleaned_data["address2"]
            city = form.cleaned_data["city"]
            state = form.cleaned_data["state"]
            postal_code = form.cleaned_data["postal_code"]
            country = form.cleaned_data["country"]
            phone = form.cleaned_data["phone"]
            language = form.cleaned_data["language"]
            timezone = form.cleaned_data["timezone"]
            currency = form.cleaned_data["currency"]

            return http.JsonResponse(status=HTTPStatus.OK, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data={})

    def post(self, request):
        self.process_form(request)

    def patch(self, request):
        self.process_form(request)

    def put(self, request):
        self.process_form(request)
