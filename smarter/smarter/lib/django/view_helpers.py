"""Django template and view helper functions."""

import logging
import re
from typing import Optional

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
from htmlmin.main import minify

from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VIEW_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

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
    The foundational base view for all Smarter platform views.

    This class serves as the root for every view within the Smarter application, providing a
    unified interface and shared functionality for web, XML, and text-based views.
    By inheriting from both Django's ``View`` and the custom ``SmarterRequestMixin``, it
    ensures consistent request handling and integration with Smarter-specific request features.

    All other view classes in the platform are designed to extend this base, inheriting its
    core logic and conventions. This approach centralizes common behaviors, such as context management,
    template rendering, HTML minification, and logging, enabling maintainable and scalable
    development across the platform.

    The ``SmarterView`` class is intended to be subclassed, allowing developers to build
    specialized views while leveraging the robust foundation it provides. It encapsulates
    essential mechanisms for error handling, template processing, and integration with platform-wide
    configuration, making it the cornerstone of the Smarter view architecture.
    """

    template_path: str = ""
    context: dict = {}

    def __init__(self, *args, **kwargs):
        """
        Initialize the SmarterView with request and other arguments.
        This method initializes the SmarterRequestMixin with the request.

        :param args: Positional arguments, where the first argument is expected to be the HttpRequest.
        :param kwargs: Keyword arguments, which may include the HttpRequest under the 'request'
                          key.
        :return: None
        :rtype: None
        """
        request: Optional[HttpRequest] = None
        if args:
            request = args[0]
        elif "request" in kwargs:
            request = kwargs["request"]

        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
        super().__init__(*args, **kwargs)

    @register.filter
    def remove_comments(self, html):
        """
        Remove HTML comments from an html string.

        :param html: The HTML string from which to remove comments.
        :type html: str
        :return: The HTML string without comments.
        :rtype: str
        """
        return re.sub(r"<!--.*?-->", "", html)

    def minify_html(self, html):
        """
        Minify an html string.

        :param html: The HTML string to minify.
        :type html: str
        :return: The minified HTML string.
        :rtype: str
        """
        return minify(html, remove_empty_space=True)

    def render_clean_html(self, request: HttpRequest, template_path, context=None):
        """
        Render a template as a string, with comments removed and minified.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param template_path: The path to the template to render.
        :type template_path: str
        :param context: The context to use for rendering the template.
        :type context: dict, optional
        :return: The rendered, cleaned HTML string.
        :rtype: str
        """
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
                exc_info=True,
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

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: The result of the superclass setup method.
        :rtype: Any
        """
        logger.info(
            "%s.setup() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
            args,
            kwargs,
        )
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
        """
        Render a template and return an HttpResponse with comments removed.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param template_path: The path to the template to render.
        :type template_path: str
        :param context: The context to use for rendering the template.
        :type context: dict, optional
        :return: An HttpResponse with the cleaned HTML content.
        :rtype: HttpResponse
        """
        minified_html = self.render_clean_html(request, template_path, context)
        return HttpResponse(content=minified_html, content_type="text/html")

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests and return a cleaned HttpResponse.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :return: An HttpResponse with the cleaned HTML content.
        :rtype: HttpResponse
        """
        return self.clean_http_response(
            request, template_path=self.template_path, context=self.context, *args, **kwargs
        )


@method_decorator(never_cache, name="dispatch")
class SmarterNeverCachedWebView(SmarterWebHtmlView):
    """
    An optimized web view that is never cached.
    """


@method_decorator(login_required, name="dispatch")
# @method_decorator(ensure_csrf_cookie, name="dispatch")
class SmarterAuthenticatedWebView(SmarterWebHtmlView):
    """
    An optimized view that requires authentication.
    Includes helpers for getting the account and user profile.
    and forces a 404 response for users without a profile.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Dispatch the request, redirecting to login if the user is anonymous.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :return: An HttpResponse object.
        :rtype: HttpResponse
        """
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
        """
        Dispatch the request and patch vary headers for successful responses.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :return: An HttpResponse object.
        :rtype: HttpResponse
        """
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
