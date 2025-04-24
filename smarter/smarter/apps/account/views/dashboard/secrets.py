"""Views for the account settings."""

# python stuff
import json
import logging
from http import HTTPStatus

# django stuff
from django import http
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseRedirect
from django.urls import reverse

# our stuff
from smarter.apps.account.admin import SecretAdminForm as SecretForm
from smarter.apps.account.models import Secret, UserProfile
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.view_helpers import SmarterAdminWebView


logger = logging.getLogger(__name__)


class SecretBase(SmarterAdminWebView):
    """Base class for Secret views."""

    user_profile: UserProfile = None

    def dispatch(self, request: WSGIRequest, *args, **kwargs):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return SmarterHttpResponseForbidden(
                request=request, error_message="You are not allowed to access this page"
            )

        self.user_profile = UserProfile.objects.get(user=request.user)
        return super().dispatch(request, *args, **kwargs)


class SecretsView(SecretBase):
    """View for the Secrets for user's account."""

    template_path = "account/dashboard/secrets.html"

    def get(self, request: WSGIRequest):
        secrets = Secret.objects.filter(user_profile=self.user_profile).only(
            "id", "name", "description", "created_at", "updated_at", "last_accessed", "expires_at"
        )
        context = {
            "account_secrets": {
                "secrets": secrets,
            }
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class SecretView(SecretBase):
    """detail View for secret management."""

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
            secret = Secret.objects.get(pk=secret_id)
        except Secret.DoesNotExist:
            return self._handle_create(request)

        if not secret.has_permissions(request=request):
            return http.JsonResponse(
                status=HTTPStatus.FORBIDDEN, data={"error": "You are not allowed to view this secret"}
            )

        data = request.POST
        secret_form = SecretForm(data, instance=secret)
        if secret_form.is_valid():
            secret = Secret.objects.get(pk=secret_id)
            secret.description = secret_form.cleaned_data["description"]
            secret.expires_at = secret_form.cleaned_data["expires_at"]
            secret.encrypted_value = Secret.encrypt(value=secret_form.cleaned_data["value"])
            secret.save()
            return http.JsonResponse(status=HTTPStatus.OK.value, data=secret_form.data)
        return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data=secret_form.errors)

    def _handle_json(self, request: WSGIRequest, secret_id):
        try:
            secret = Secret.objects.get(pk=secret_id)
        except Secret.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"error": "Secret not found"})

        data = json.loads(request.body)
        secret_form = SecretForm(data, instance=secret)
        if secret_form.is_valid():
            secret.description = secret_form.cleaned_data["description"]
            secret.expires_at = secret_form.cleaned_data["expires_at"]
            secret.encrypted_value = Secret.encrypt(value=secret_form.cleaned_data["value"])
            secret.save()

        return http.JsonResponse(status=HTTPStatus.OK.value, data={})

    def _handle_write_request(self, request: WSGIRequest, secret_id):
        if request.content_type == "multipart/form-data":
            return self._handle_multipart_form(request, secret_id)
        if request.content_type == "application/json":
            return self._handle_json(request, secret_id)
        return http.JsonResponse({"error": "Invalid content type"}, status=400)

    # pylint: disable=W0221
    def get(self, request: WSGIRequest, secret_id: int = None, new_secret: str = None):
        """Get the secret. We also use this to create a new secret."""

        # in cases where we arrived here via api-keys/new/
        if secret_id is None:
            return SmarterHttpResponseNotFound(request=request, error_message="Secret not found")

        try:
            # cases where we received an int pk identifier for an existing secret
            secret = Secret.objects.get(pk=secret_id)
            secret_form = SecretForm(instance=secret)
            if not secret.has_permissions(request=request):
                return http.JsonResponse(
                    status=HTTPStatus.FORBIDDEN.value, data={"error": "You are not allowed to view this secret"}
                )
        except (Secret.DoesNotExist, ValueError):
            return SmarterHttpResponseNotFound(request=request, error_message="Secret not found")

        context = {
            "account_secrets": {
                "secret": secret,
                "is_new": new_secret is not None,
                "secret_form": secret_form,
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
            secret = Secret.objects.get(pk=secret_id)
        except Secret.DoesNotExist:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"error": "Secret not found"})
        if not secret.has_permissions(request=request):
            return SmarterHttpResponseForbidden(
                request=request, error_message="You are not allowed to delete this secret"
            )
        secret.delete()
        return http.JsonResponse(status=HTTPStatus.OK.value, data={})
