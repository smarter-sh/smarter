"""Views for the account settings."""

# python stuff
import json
import logging
from http import HTTPStatus

# django stuff
from django import http
from django.core.handlers.wsgi import WSGIRequest

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
    secret: Secret = None

    def _handle_multipart_form(self, request: WSGIRequest):
        """
        Handle multipart form data for both edit and create secret.
        """
        data = request.POST
        secret_form = SecretForm(data, instance=self.secret)
        if not secret_form.is_valid():
            return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data=secret_form.errors)

        name = secret_form.cleaned_data["name"]
        description = secret_form.cleaned_data["description"]
        expires_at = secret_form.cleaned_data["expires_at"]
        encrypted_value = Secret.encrypt(value=secret_form.cleaned_data["value"])
        if self.secret:
            self.secret.description = description
            self.secret.expires_at = expires_at
            self.secret.encrypted_value = encrypted_value
            logger.info("%s is editing secret: %s", self.user_profile.user.username, name)
        else:
            self.secret = Secret(
                user_profile=self.user_profile,
                name=name,
                description=description,
                expires_at=expires_at,
                encrypted_value=encrypted_value,
            )
            logger.info("%s is creating secret: %s", self.user_profile.user.username, name)
        self.secret.save()
        logger.info("%s saved secret: %s", self.user_profile.user.username, name)
        return http.JsonResponse(status=HTTPStatus.OK.value, data=secret_form.data)

    def _handle_json(self, request: WSGIRequest):
        if not self.secret:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"error": "Secret not found"})

        data = json.loads(request.body)
        secret_form = SecretForm(data, instance=self.secret)
        if secret_form.is_valid():
            self.secret.description = secret_form.cleaned_data["description"]
            self.secret.expires_at = secret_form.cleaned_data["expires_at"]
            self.secret.encrypted_value = Secret.encrypt(value=secret_form.cleaned_data["value"])
            self.secret.save()

        return http.JsonResponse(status=HTTPStatus.OK.value, data={})

    def _handle_write_request(self, request: WSGIRequest):
        if not self.secret:
            return SmarterHttpResponseNotFound(request=request, error_message="Secret not found")
        if request.content_type == "multipart/form-data":
            return self._handle_multipart_form(request)
        if request.content_type == "application/json":
            return self._handle_json(request)
        return http.JsonResponse({"error": "Invalid content type"}, status=400)

    def dispatch(self, request: WSGIRequest, *args, **kwargs):

        secret_id: int = kwargs.get("secret_id")
        if secret_id:
            logger.info("SecretView.dispatch() secret_id: %s", secret_id)
            try:
                self.secret = Secret.objects.get(pk=secret_id, user_profile=self.user_profile)
            except Secret.DoesNotExist:
                return SmarterHttpResponseNotFound(request=request, error_message="Secret not found")
            if not self.secret.has_permissions(request=request):
                return http.JsonResponse(
                    status=HTTPStatus.FORBIDDEN.value, data={"error": "You are not allowed to view this secret"}
                )
        else:
            logger.info("SecretView.dispatch() with no secret_id")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: WSGIRequest, secret_id: int = None):

        secret_form = SecretForm(instance=self.secret)
        context = {
            "account_secret": {
                "secret": self.secret,
                "is_new": secret_id is None,
                "form": secret_form,
            }
        }

        # case 1: create a new secret
        # ie. we arrived here via /account/dashboard/secrets/new/
        if not self.secret:
            logger.info("%s is creating a new secret", self.user_profile.user.username)
            return self.clean_http_response(request, template_path=self.template_path, context=context)

        # case 2: edit an existing secret
        logger.info("%s got secret: %s", self.user_profile.user.username, secret_id)
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request: WSGIRequest):
        logger.info("%s posted a new secret", self.user_profile.user.username)
        return self._handle_multipart_form(request)

    # pylint: disable=W0613
    def patch(self, request: WSGIRequest, secret_id):
        if not self.secret:
            return SmarterHttpResponseNotFound(request=request, error_message="Secret not found")
        logger.info("%s patched secret: %s", self.user_profile.user.username, secret_id)
        return self._handle_write_request(request)

    def delete(self, request: WSGIRequest, secret_id):
        if not self.secret:
            return SmarterHttpResponseNotFound(request=request, error_message="Secret not found")
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
        logger.info("%s deleted secret: %s", self.user_profile.user.username, secret_id)
        return http.JsonResponse(status=HTTPStatus.OK.value, data={})
