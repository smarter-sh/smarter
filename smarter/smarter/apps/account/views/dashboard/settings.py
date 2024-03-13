# -*- coding: utf-8 -*-
"""Views for the account settings."""
from http import HTTPStatus

from django import forms, http

from smarter.view_helpers import SmarterAuthenticatedWebView


class ProfileForm(forms.Form):
    """Form for Payment methods modal."""

    first_name = forms.CharField()
    last_name = forms.CharField()
    company_name = forms.CharField()
    phone = forms.CharField()
    country = forms.CharField()
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
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            company_name = form.cleaned_data["company_name"]
            phone = form.cleaned_data["phone"]
            country = form.cleaned_data["country"]
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
