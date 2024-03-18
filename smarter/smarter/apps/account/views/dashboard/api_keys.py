# -*- coding: utf-8 -*-
"""Views for the account settings."""
import json
import logging
from http import HTTPStatus

from django import forms, http
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict

from smarter.apps.account.models import APIKey, UserProfile
from smarter.apps.common.view_helpers import SmarterAdminWebView


User = get_user_model()
logger = logging.getLogger(__name__)
excluded_fields = ["password", "date_joined"]


class APIKeyForm(forms.ModelForm):
    """Form for api key management."""

    class Meta:
        """Meta class for APIKeyForm with all fields."""

        model = APIKey
        fields = ["user", "description", "is_active"]


class APIKeysView(SmarterAdminWebView):
    """View for the account API keys."""

    template_path = "account/dashboard/api-keys.html"

    def get(self, request):
        account = UserProfile.objects.get(user=request.user).account
        api_keys = APIKey.objects.filter(account=account).only(
            "user", "description", "created_at", "last_used_at", "is_active"
        )
        context = {
            "account_apikeys": {
                "api_keys": api_keys,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class APIKeyView(SmarterAdminWebView):
    """detail View for api key management."""

    template_path = "account/dashboard/api-key.html"

    def _handle_create(self, request):
        post_data = request.POST.copy()  # Make a mutable copy
        post_data["user"] = request.user.id  # Set the user field's value
        apikey_form = APIKeyForm(post_data)
        if apikey_form.is_valid():
            apikey = apikey_form.save()
            new_api_key = APIKey.objects.get(digest=apikey.digest)
            api_key_dict = model_to_dict(new_api_key)
            api_key_dict["key_id"] = new_api_key.key_id

            return http.JsonResponse(status=HTTPStatus.CREATED, data=api_key_dict)
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=apikey_form.errors)

    def _handle_multipart_form(self, request, key_id):

        try:
            apikey = APIKey.objects.get(key_id=key_id)
        except APIKey.DoesNotExist:
            return self._handle_create(request)

        if not apikey.has_permissions(user=request.user):
            return http.JsonResponse(
                status=HTTPStatus.FORBIDDEN, data={"error": "You are not allowed to view this api key"}
            )

        apikey_form = APIKeyForm(request.POST, instance=apikey)
        if apikey_form.is_valid():
            apikey_form.save()
            return http.JsonResponse(status=HTTPStatus.OK, data=apikey_form.data)
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=apikey_form.errors)

    def _handle_json(self, request, key_id):
        try:
            api_key = APIKey.objects.get(key_id=key_id)
        except APIKey.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND, data={"error": "API Key not found"})

        data = json.loads(request.body)
        action = str(data.get("action", "")).lower()

        events = {
            "activate": api_key.activate,
            "deactivate": api_key.deactivate,
            "toggle_active": api_key.toggle_active,
        }
        event_func = events.get(action)
        if event_func is None:
            return http.JsonResponse({"error": "Unrecognized action"}, status=400)
        event_func()

        return http.JsonResponse(status=HTTPStatus.OK, data={})

    def _handle_write_request(self, request, key_id):
        if request.content_type == "multipart/form-data":
            return self._handle_multipart_form(request, key_id)
        if request.content_type == "application/json":
            return self._handle_json(request, key_id)
        return http.JsonResponse({"error": "Invalid content type"}, status=400)

    # pylint: disable=W0221
    def get(self, request, key_id):
        """Get the api key. We also use this to create a new api key."""
        try:
            apikey = APIKey.objects.get(key_id=key_id)
            apikey_form = APIKeyForm(instance=apikey)
            if not apikey.has_permissions(user=request.user):
                return http.JsonResponse(
                    status=HTTPStatus.FORBIDDEN, data={"error": "You are not allowed to view this api key"}
                )
        except APIKey.DoesNotExist:
            return http.HttpResponseNotFound({"error": "API Key not found"})

        context = {
            "account_apikeys": {
                "api_key": apikey,
                "apikey_form": apikey_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, key_id=None):
        print("APIKeyView.post")
        if key_id is None:
            return self._handle_create(request)
        return self._handle_write_request(request, key_id)

    def patch(self, request, key_id=None):
        if key_id is None:
            return self._handle_create(request)
        return self._handle_write_request(request, key_id)

    def put(self, request, key_id=None):
        if key_id is None:
            return self._handle_create(request)
        return self._handle_write_request(request, key_id)

    def delete(self, request, key_id):
        try:
            apikey = APIKey.objects.get(key_id=key_id)
        except APIKey.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND, data={"error": "API Key not found"})
        if not apikey.has_permissions(user=request.user):
            return http.HttpResponseForbidden({"error": "You are not allowed to delete this api key"})
        apikey.delete()
        return http.JsonResponse(status=HTTPStatus.OK, data={})
