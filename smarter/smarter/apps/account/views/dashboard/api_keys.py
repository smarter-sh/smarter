# -*- coding: utf-8 -*-
"""Views for the account settings."""
import json
import logging
from http import HTTPStatus
from uuid import UUID

from django import forms, http
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.urls import reverse

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
        fields = ["description", "is_active"]


class APIKeysView(SmarterAdminWebView):
    """View for the account API keys."""

    template_path = "account/dashboard/api-keys.html"

    def get(self, request):
        account = UserProfile.objects.get(user=request.user).account
        api_keys = APIKey.objects.filter(account=account).only(
            "user", "description", "created", "last_used_at", "is_active"
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
        new_api_key, token = APIKey.objects.create(
            user=request.user, expiry=None, description=f"New API key created by {request.user}"
        )
        url = reverse(
            "account_new_api_key",
            kwargs={
                "key_id": new_api_key.key_id,
                "new_api_key": token,
            },
        )
        return HttpResponseRedirect(url)

    def _handle_multipart_form(self, request, key_id):
        try:
            apikey = APIKey.objects.get(key_id=key_id)
        except APIKey.DoesNotExist:
            return self._handle_create(request)

        if not apikey.has_permissions(user=request.user):
            return http.JsonResponse(
                status=HTTPStatus.FORBIDDEN, data={"error": "You are not allowed to view this api key"}
            )

        data = request.POST
        apikey_form = APIKeyForm(data, instance=apikey)
        if apikey_form.is_valid():
            api_key = APIKey.objects.get(key_id=key_id)
            api_key.description = apikey_form.cleaned_data["description"]
            api_key.is_active = apikey_form.cleaned_data["is_active"]
            api_key.save()
            return http.JsonResponse(status=HTTPStatus.OK, data=apikey_form.data)
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST, data=apikey_form.errors)

    def _handle_json(self, request, key_id):
        try:
            api_key = APIKey.objects.get(key_id=key_id)
        except APIKey.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND, data={"error": "API Key not found"})

        data = json.loads(request.body)
        if "action" in data:
            action = str(data.get("action", "")).lower()
            events = {
                "activate": api_key.activate,
                "deactivate": api_key.deactivate,
                "toggle_active": api_key.toggle_active,
            }
            event_func = events.get(action)
            if event_func is None:
                return http.JsonResponse({"error": f"Unrecognized action: {event_func}"}, status=400)
            event_func()
        else:
            apikey_form = APIKeyForm(data, instance=api_key)
            if apikey_form.is_valid():
                api_key.description = apikey_form.cleaned_data["description"]
                api_key.is_active = apikey_form.cleaned_data["is_active"]
                api_key.save()

        return http.JsonResponse(status=HTTPStatus.OK, data={})

    def _handle_write_request(self, request, key_id):
        if request.content_type == "multipart/form-data":
            return self._handle_multipart_form(request, key_id)
        if request.content_type == "application/json":
            return self._handle_json(request, key_id)
        return http.JsonResponse({"error": "Invalid content type"}, status=400)

    def is_valid_uuid(self, uuid_to_test, version=4):
        """Check if uuid_to_test is a valid UUID."""
        if isinstance(uuid_to_test, UUID):
            uuid_to_test = str(uuid_to_test)
        try:
            uuid_obj = UUID(uuid_to_test, version=version)
        except ValueError:
            return False

        return str(uuid_obj) == uuid_to_test

    # pylint: disable=W0221
    def get(self, request, key_id: str = None, new_api_key: str = None):
        """Get the api key. We also use this to create a new api key."""

        # in cases where we arrived here via api-keys/new/
        if key_id is None:
            return self._handle_create(request)
        if not self.is_valid_uuid(key_id):
            return http.HttpResponseNotFound({"error": "Invalid key_id"})

        try:
            # cases where we received a uuid identifier for an existing api key
            apikey = APIKey.objects.get(key_id=key_id)
            apikey_form = APIKeyForm(instance=apikey)
            if not apikey.has_permissions(user=request.user):
                return http.JsonResponse(
                    status=HTTPStatus.FORBIDDEN, data={"error": "You are not allowed to view this api key"}
                )

            # ensure that the string value we received is a valid token that
            # can actually be used to authenticate via Django.
            if new_api_key:
                apikey.validate_token(new_api_key)
        except (APIKey.DoesNotExist, ValueError):
            return http.HttpResponseNotFound({"error": "API Key not found"})

        context = {
            "account_apikeys": {
                "api_key": apikey,
                "token_key": new_api_key or "****" + apikey.token_key,
                "is_new": new_api_key is not None,
                "apikey_form": apikey_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        return self._handle_create(request)

    def patch(self, request, key_id):
        logger.info("Received PATCH request: %s", request)

        return self._handle_write_request(request, key_id)

    def delete(self, request, key_id):
        logger.info("Received DELETE request: %s", request)
        try:
            apikey = APIKey.objects.get(key_id=key_id)
        except APIKey.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND, data={"error": "API Key not found"})
        if not apikey.has_permissions(user=request.user):
            return http.HttpResponseForbidden({"error": "You are not allowed to delete this api key"})
        apikey.delete()
        return http.JsonResponse(status=HTTPStatus.OK, data={})
