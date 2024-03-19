# -*- coding: utf-8 -*-
"""Django template and view helper functions."""
import re

from django import template
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control, cache_page, never_cache
from htmlmin.main import minify
from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from smarter.apps.account.models import APIKey
from smarter.apps.common.decorators import staff_required


register = template.Library()


def redirect_and_expire_cache(path: str = "/"):
    """Redirect to the given path and expire the cache."""
    response = redirect(path)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


class SmarterTokenAuthentication(TokenAuthentication):
    """
    Custom token authentication for smarter.
    This is used to authenticate API keys. It is a subclass of the default knox
    behavior, but it also checks that the API key is active.
    """

    model = APIKey

    def authenticate_credentials(self, token):
        # authenticate the user using the normal token authentication
        # this will raise an AuthenticationFailed exception if the token is invalid
        user, auth_token = super().authenticate_credentials(token)

        try:
            # next, we need to ensure that the token is active, otherwise
            # we should raise an exception that exactly matches the one
            # raised by the default token authentication
            APIKey.objects.get(token_key=auth_token.token_key, is_active=True)

            # if the token is active, we can return the user and token as a tuple
            # exactly as the default token authentication does.
            return (user, auth_token)
        except APIKey.DoesNotExist as e:
            raise AuthenticationFailed from e


# ------------------------------------------------------------------------------
# API Views
# ------------------------------------------------------------------------------
class IsStaffUser(BasePermission):
    """
    Custom permission to only allow access to staff users.
    """

    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


class SmarterAPIAuthenticated(IsAuthenticated):
    """
    Allows access only to authenticated users.
    """


class SmarterAPIAdmin(SmarterAPIAuthenticated, IsStaffUser):
    """
    Allows access only to admins.
    """


class SmarterAPIView(APIView):
    """Base API view for smarter."""

    permission_classes = [SmarterAPIAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]


class SmarterAPIListView(ListAPIView):
    """Base API listview for smarter."""

    permission_classes = [SmarterAPIAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]
    http_method_names = ["get"]


class SmarterAPIAdminView(SmarterAPIView):
    """Base admin-only API view."""

    permission_classes = [SmarterAPIAdmin]


class SmarterAPIListAdminView(SmarterAPIListView):
    """Base admin-only API list view."""

    permission_classes = [SmarterAPIAdmin]


# ------------------------------------------------------------------------------
# Web Views
# ------------------------------------------------------------------------------
class SmarterWebView(View):
    """
    Base view for smarter web views.
    Includes helpers for rendering, minifying and stripping out developer comments.
    """

    template_path: str = ""
    context: dict = {}

    @register.filter
    def remove_comments(self, html):
        """Remove HTML comments from an html string."""
        return re.sub(r"<!--.*?-->", "", html)

    def minify_html(self, html):
        """Minify an html string."""
        return minify(html, remove_empty_space=True)

    def render_clean_html(self, request, template_path, context=None):
        """Render a template as a string, with comments removed and minified."""
        context = context or self.context
        response = render(request=request, template_name=template_path, context=context)
        html = response.content.decode(response.charset)
        html_no_comments = self.remove_comments(html=html)
        minified_html = self.minify_html(html=html_no_comments)
        return minified_html

    # pylint: disable=W0613
    def clean_http_response(self, request, template_path, context=None):
        """Render a template and return an HttpResponse with comments removed."""
        minified_html = self.render_clean_html(request, template_path, context)
        return HttpResponse(content=minified_html, content_type="text/html")

    def get(self, request):
        return self.clean_http_response(request, template_path=self.template_path)


class SmarterNeverCachedWebView(SmarterWebView):
    """An optimized web view that is never cached."""

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedWebView(SmarterWebView):
    """An optimized view that requires authentication."""


@method_decorator(cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
@method_decorator(cache_page(settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
class SmarterAuthenticatedCachedWebView(SmarterAuthenticatedWebView):
    """An optimized and cached web view that requires authentication."""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        patch_vary_headers(response, ["Cookie"])
        return response


class SmarterAuthenticatedNeverCachedWebView(SmarterAuthenticatedWebView):
    """An optimized web view that requires authentication and is never cached."""

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


@method_decorator(staff_required, name="dispatch")
class SmarterAdminWebView(SmarterAuthenticatedNeverCachedWebView):
    """An admin-only optimized web view that is never cached."""
