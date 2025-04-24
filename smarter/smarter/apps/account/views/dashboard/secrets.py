"""Views for the account settings."""

import json
import logging
from http import HTTPStatus
from uuid import UUID

from django import http
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseRedirect
from django.urls import reverse

from smarter.apps.account.admin import SecretAdminForm as SecretForm
from smarter.apps.account.models import Account, Secret, UserProfile
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.view_helpers import SmarterAdminWebView


logger = logging.getLogger(__name__)


class SecretBase(SmarterAdminWebView):
    """Base class for Secret views."""

    account: Account = None
    user_profile: UserProfile = None

    def dispatch(self, request: WSGIRequest, *args, **kwargs):
        self.user_profile = UserProfile.objects.get(user=request.user)
        self.account = self.user_profile.account
        return super().dispatch(request, *args, **kwargs)


class SecretsView(SecretBase):
    """View for the account Secrets."""

    template_path = "account/dashboard/secrets.html"

    def get(self, request: WSGIRequest):
        secrets = Secret.objects.filter(user_profile=self.user_profile).only(
            "name", "description", "created_at", "modified_at", "last_accessed", "expires_at"
        )
        context = {
            "account_secrets": {
                "secrets": secrets,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class SecretView(SecretBase):
    """detail View for api key management."""

    template_path = "account/dashboard/secret.html"

    def _handle_create(self, request: WSGIRequest):
        new_secret = Secret.objects.create(
            name="New Secret", user_profile=self.user_profile, description=f"New Secret created by {request.user}"
        )
        url = reverse(
            "account_new_secret",
            kwargs={
                "secret_id": new_secret.id,
                "new_secret": new_secret.get_secret(update_last_accessed=False),
            },
        )
        return HttpResponseRedirect(url)

    def _handle_multipart_form(self, request: WSGIRequest, secret_id):
        try:
            apikey = Secret.objects.get(secret_id=secret_id)
        except Secret.DoesNotExist:
            return self._handle_create(request)

        if not apikey.has_permissions(user=request.user):
            return http.JsonResponse(
                status=HTTPStatus.FORBIDDEN, data={"error": "You are not allowed to view this api key"}
            )

        data = request.POST
        apikey_form = SecretForm(data, instance=apikey)
        if apikey_form.is_valid():
            api_key = Secret.objects.get(secret_id=secret_id)
            api_key.description = apikey_form.cleaned_data["description"]
            api_key.is_active = apikey_form.cleaned_data["is_active"]
            api_key.save()
            return http.JsonResponse(status=HTTPStatus.OK.value, data=apikey_form.data)
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data=apikey_form.errors)

    def _handle_json(self, request: WSGIRequest, secret_id):
        try:
            api_key = Secret.objects.get(secret_id=secret_id)
        except Secret.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"error": "Secret not found"})

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
            apikey_form = SecretForm(data, instance=api_key)
            if apikey_form.is_valid():
                api_key.description = apikey_form.cleaned_data["description"]
                api_key.is_active = apikey_form.cleaned_data["is_active"]
                api_key.save()

        return http.JsonResponse(status=HTTPStatus.OK.value, data={})

    def _handle_write_request(self, request: WSGIRequest, secret_id):
        if request.content_type == "multipart/form-data":
            return self._handle_multipart_form(request, secret_id)
        if request.content_type == "application/json":
            return self._handle_json(request, secret_id)
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
    def get(self, request: WSGIRequest, secret_id: str = None, new_secret: str = None):
        """Get the api key. We also use this to create a new api key."""

        # in cases where we arrived here via api-keys/new/
        if secret_id is None:
            return self._handle_create(request)
        if not self.is_valid_uuid(secret_id):
            return SmarterHttpResponseNotFound(request=request, error_message="Invalid Secret")

        try:
            # cases where we received a uuid identifier for an existing api key
            apikey = Secret.objects.get(secret_id=secret_id)
            apikey_form = SecretForm(instance=apikey)
            if not apikey.has_permissions(user=request.user):
                return http.JsonResponse(
                    status=HTTPStatus.FORBIDDEN.value, data={"error": "You are not allowed to view this api key"}
                )

            # ensure that the string value we received is a valid token that
            # can actually be used to authenticate via Django.
            if new_secret:
                if not apikey.validate_token(new_secret):
                    raise ValueError("Invalid token")
        except (Secret.DoesNotExist, ValueError):
            return SmarterHttpResponseNotFound(request=request, error_message="Secret not found")

        context = {
            "account_secrets": {
                "api_key": apikey,
                "token_key": new_secret or "****" + apikey.token_key,
                "is_new": new_secret is not None,
                "apikey_form": apikey_form,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request: WSGIRequest):
        return self._handle_create(request)

    def patch(self, request: WSGIRequest, secret_id):
        logger.info("Received PATCH request: %s", request)

        return self._handle_write_request(request, secret_id)

    def delete(self, request: WSGIRequest, secret_id):
        logger.info("Received DELETE request: %s", request)
        try:
            apikey = Secret.objects.get(secret_id=secret_id)
        except Secret.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"error": "Secret not found"})
        if not apikey.has_permissions(user=request.user):
            return SmarterHttpResponseForbidden(
                request=request, error_message="You are not allowed to delete this api key"
            )
        apikey.delete()
        return http.JsonResponse(status=HTTPStatus.OK.value, data={})
