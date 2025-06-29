"""Django template and view helper functions."""

import logging
import re

from django import template
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control, cache_page, never_cache

# from django.views.decorators.csrf import ensure_csrf_cookie
from htmlmin.main import minify

from smarter.lib.django.request import SmarterRequestMixin


logger = logging.getLogger(__name__)
register = template.Library()


def redirect_and_expire_cache(path: str = "/"):
    """Redirect to the given path and expire the cache."""
    response = redirect(path)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# ------------------------------------------------------------------------------
# Web Views
# ------------------------------------------------------------------------------
class SmarterView(View, SmarterRequestMixin):
    """
    Base view for smarter views.
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

    def render_clean_html(self, request: HttpRequest, template_path, context=None):
        """Render a template as a string, with comments removed and minified."""
        context = context or self.context
        response = None
        try:
            response = render(request=request, template_name=template_path, context=context)
        # pylint: disable=W0718
        except Exception as e:
            logger.error(
                "%s.render_clean_html(): %s, %s. error: %s",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request),
                template_path,
                e,
            )
            return HttpResponse(status=500)

        html = response.content.decode(response.charset)
        html_no_comments = self.remove_comments(html=html)
        minified_html = self.minify_html(html=html_no_comments)
        return minified_html

    def setup(self, request: HttpRequest, *args, **kwargs):
        """
        Setup the view with the request and any additional arguments.
        This method initializes the SmarterRequestMixin with the request.
        """
        logger.info("%s.setup() - request: %s, args: %s, kwargs: %s", self.formatted_class_name, request, args, kwargs)
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)
        return super().setup(request, *args, **kwargs)


class SmarterWebXmlView(SmarterView):
    """
    Base view for smarter xml web views.
    """

    def get(self, request):
        return render(request=request, template_name=self.template_path, context=self.context)


class SmarterWebTxtView(SmarterView):
    """
    Base view for smarter xml web views.
    """

    def get(self, request):
        minified_html = self.render_clean_html(request, template_path=self.template_path, context=self.context)
        return HttpResponse(content=minified_html, content_type="text/plain")


class SmarterWebHtmlView(SmarterView):
    """
    Base view for smarter web views.
    Includes helpers for rendering, minifying and stripping out developer comments.
    """

    # pylint: disable=W0613
    def clean_http_response(self, request: HttpRequest, template_path, *args, context=None, **kwargs):
        """Render a template and return an HttpResponse with comments removed."""
        minified_html = self.render_clean_html(request, template_path, context)
        return HttpResponse(content=minified_html, content_type="text/html")

    def get(self, request, *args, **kwargs):
        return self.clean_http_response(
            request, template_path=self.template_path, context=self.context, *args, **kwargs
        )


@method_decorator(never_cache, name="dispatch")
class SmarterNeverCachedWebView(SmarterWebHtmlView):
    """An optimized web view that is never cached."""


@method_decorator(login_required, name="dispatch")
# @method_decorator(ensure_csrf_cookie, name="dispatch")
class SmarterAuthenticatedWebView(SmarterWebHtmlView):
    """
    An optimized view that requires authentication.
    Includes helpers for getting the account and user profile.
    and forces a 404 response for users without a profile.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs):

        if request.user.is_anonymous:
            return redirect_and_expire_cache(path="/login/")

        response = super().dispatch(request, *args, **kwargs)
        patch_vary_headers(response, ["Cookie"])
        return response


@method_decorator(cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
@method_decorator(cache_page(settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
class SmarterAuthenticatedCachedWebView(SmarterAuthenticatedWebView):
    """An optimized and cached web view that requires authentication."""

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        patch_vary_headers(response, ["Cookie"])
        return response


@method_decorator(never_cache, name="dispatch")
class SmarterAuthenticatedNeverCachedWebView(SmarterAuthenticatedWebView):
    """An optimized web view that requires authentication and is never cached."""


@method_decorator(staff_member_required, name="dispatch")
class SmarterAdminWebView(SmarterAuthenticatedNeverCachedWebView):
    """An admin-only optimized web view that is never cached."""
