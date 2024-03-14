# -*- coding: utf-8 -*-
"""Views for the account settings."""
import logging
from http import HTTPStatus

from django import forms, http
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from smarter.apps.account.models import APIKey, UserProfile
from smarter.view_helpers import SmarterAdminWebView


User = get_user_model()
logger = logging.getLogger(__name__)
excluded_fields = ["password", "date_joined"]


class APIKeyForm(forms.ModelForm):
    """Form for api key management."""

    class Meta:
        """Meta class for APIKeyForm with all fields."""

        model = APIKey
        fields = "__all__"


class APIKeysView(SmarterAdminWebView):
    """View for the account API keys."""

    template_path = "account/dashboard/api-keys.html"

    def get(self, request):
        account = UserProfile.objects.get(user=request.user).account
        api_keys = APIKey.objects.filter(account=account).only(
            "user", "description", "created_at", "last_used_at", "is_active"
        )
        api_keys_with_identifier = [
            {
                "user": api_key.user,
                "description": api_key.description,
                "identifier": api_key.identifier,
                "created_at": api_key.created_at,
                "last_used_at": api_key.last_used_at,
                "is_active": api_key.is_active,
            }
            for api_key in api_keys
        ]

        logger.info("API keys: %s", api_keys_with_identifier)
        context = {
            "account_apikeys": {
                "api_keys": api_keys_with_identifier,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class APIKeyView(SmarterAdminWebView):
    """detail View for api key management."""

    template_path = "account/dashboard/api-key.html"

    def _handle_create(self, request):
        apikey_form = APIKeyForm(request.POST)
        if apikey_form.is_valid():
            apikey = apikey_form.save()
            return redirect("account_user", apikey_id=apikey.id)
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=apikey_form.errors)

    def _handle_write(self, request, apikey_id):

        try:
            apikey = APIKey.objects.get(id=apikey_id)
        except APIKey.DoesNotExist:
            return self._handle_create(request)

        apikey_form = APIKeyForm(request.POST, instance=apikey)
        if apikey_form.is_valid():
            apikey_form.save()
            return http.JsonResponse(status=HTTPStatus.OK, data={})
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=apikey_form.errors)

    # pylint: disable=W0221
    def get(self, request, apikey_id):
        """Get the api key. We also use this to create a new api key."""
        try:
            apikey = APIKey.objects.get(id=apikey_id)
            apikey_form = APIKeyForm(instance=apikey)

            # Check if the user is allowed to manage this api key
            apikey_userprofile = UserProfile.objects.get(user=apikey.user)
            user_profile = UserProfile.objects.get(user=request.user)
            if apikey_userprofile.account != user_profile.account:
                return http.HttpResponseForbidden({"error": "You are not allowed to view this api key"})
        except APIKey.DoesNotExist:
            apikey = None
            apikey_form = APIKeyForm()

        context = {
            "account_apikeys": {
                "api_key": apikey,
                "apikey_form": apikey_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, apikey_id):
        return self._handle_write(request, apikey_id)

    def patch(self, request, apikey_id):
        return self._handle_write(request, apikey_id)

    def put(self, request, apikey_id):
        return self._handle_write(request, apikey_id)
