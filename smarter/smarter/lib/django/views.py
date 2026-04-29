"""Django template and view helper functions."""

import re
from functools import wraps
from http import HTTPStatus

from bs4 import BeautifulSoup
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control, cache_page, never_cache

from smarter.apps.account.models import Account, User, UserProfile
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text, formatted_text_blue
from smarter.lib import logging
from smarter.lib.cache import lazy_cache
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VIEW_LOGGING])
verbose_logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.VIEW_LOGGING], condition_func=should_log_verbose
)
logger_prefix = formatted_text(__name__)
logger_prefix_invalidations = formatted_text_blue(f"{__name__}.smarter_cache_page_by_user.invalidate()")

register = template.Library()
cache_prefix = f"{__name__}.smarter_cache_page_by_user"


def redirect_and_expire_cache(path: str = "/"):
    """Redirect to the given path and expire the cache."""
    response = redirect(path)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def smarter_cache_page_by_user(timeout):
    """
    Decorator to cache a view's response based on the authenticated user.
    This decorator applies Django's `cache_page` decorator with a cache key
    that is unique to each user. Authenticated users will have their
    responses cached separately, while anonymous users will share a single
    cache entry.

    Example:

        .. code-block:: python

            @method_decorator(smarter_cache_page_by_user(60 * 15), name="dispatch")
            class MyView(SmarterAuthenticatedWebView):
            ...

    :param timeout: The cache timeout in seconds.
    :type timeout: int
    :return: A decorator that can be applied to a Django view function or method.
    :rtype: function
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_SMARTER_PAGE_CACHING):
                return view_func(request, *args, **kwargs)
            path = str(request.path).replace("/", ".").strip(".")
            if hasattr(request, "user") and request.user.is_authenticated:
                key_prefix = f"{cache_prefix}.user_{request.user.id}.{path}"
            else:
                key_prefix = f"{cache_prefix}.user_anon.{path}"
            verbose_logger.debug(
                "%s - %s with cache key_prefix: %s and timeout %s", logger_prefix, path, key_prefix, timeout
            )
            return cache_page(timeout, key_prefix=key_prefix)(view_func)(request, *args, **kwargs)

        def invalidate(request: HttpRequest, *args, **kwargs):
            if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_SMARTER_PAGE_CACHING):
                return
            verbose_logger.debug(
                "%s called with request: %s, args: %s, kwargs: %s", logger_prefix_invalidations, request, args, kwargs
            )
            if request:
                path = str(request.path).replace("/", ".").strip(".")
                if hasattr(request, "user") and request.user.is_authenticated:
                    key_prefix = f"{cache_prefix}.user_{request.user.id}.{path}"  # type: ignore[union-attr]
                else:
                    key_prefix = f"{cache_prefix}.user_anon.{path}"
                verbose_logger.debug("%s searching cache for key_prefix: %s", logger_prefix_invalidations, key_prefix)
                hit = lazy_cache.get(key_prefix)
                if hit is not None:
                    lazy_cache.delete(key_prefix)
                    logger.info("%s Cache invalidated for key_prefix: %s", logger_prefix_invalidations, key_prefix)

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


# ------------------------------------------------------------------------------
# Web Views
# ------------------------------------------------------------------------------
class SmarterView(View, SmarterRequestMixin):
    """
    The foundational base view for all Smarter platform views.

    This class serves as the root for every view within the Smarter application, providing a
    unified interface and shared functionality for web, XML, and text-based views.

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
        verbose_logger.debug("%s.__init__() called with args: %s, kwargs: %s", self.logger_prefix, args, kwargs)
        super().__init__(*args, **kwargs)

        # none of these are actually expected until sometime between dispatch() and setup()
        request = kwargs.pop("request", None) or next((arg for arg in args if isinstance(arg, HttpRequest)), None)
        user = kwargs.pop("user", None) or next((arg for arg in args if isinstance(arg, User)), None)
        account = kwargs.pop("account", None) or next((arg for arg in args if isinstance(arg, Account)), None)
        user_profile = kwargs.pop("user_profile", None) or next(
            (arg for arg in args if isinstance(arg, UserProfile)), None
        )
        SmarterRequestMixin.__init__(
            self, request=request, user=user, account=account, user_profile=user_profile, *args, **kwargs
        )

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterView.__name__}")

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
        soup = BeautifulSoup(html, "html.parser")
        for element in soup.find_all(text=True):
            if isinstance(element, str) and element.isspace():
                element.extract()
        return str(soup)

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
                self.logger_prefix,
                self.smarter_build_absolute_uri(request),
                template_path,
                e,
                exc_info=True,
            )
            return HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)

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
        verbose_logger.debug(
            "%s.setup() called with request: %s, args: %s, kwargs: %s", self.logger_prefix, request, args, kwargs
        )
        if not self.smarter_request:
            self.smarter_request = (
                request or kwargs["request"] or next((arg for arg in args if isinstance(arg, HttpRequest)), None)
            )
            if self.smarter_request:
                verbose_logger.debug(
                    "%s.setup() - SmarterRequestMixin.smarter_request initialized successfully.",
                    self.logger_prefix,
                )
            else:
                logger.warning(
                    "%s.setup() - SmarterRequestMixin.smarter_request could not be initialized.",
                    self.logger_prefix,
                )
        return super().setup(request, *args, **kwargs)


class SmarterWebXmlView(SmarterView):
    """
    Base view for smarter xml web views.
    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterWebXmlView.__name__}")

    def get(self, request):
        return render(request=request, template_name=self.template_path, context=self.context)


class SmarterWebTxtView(SmarterView):
    """
    Base view for smarter xml web views.
    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterWebTxtView.__name__}")

    def get(self, request):
        minified_html = self.render_clean_html(request, template_path=self.template_path, context=self.context)
        return HttpResponse(content=minified_html, content_type="text/plain")


class SmarterWebHtmlView(SmarterView):
    """
    Base view for smarter web views.
    Includes helpers for rendering, minifying and stripping out developer comments.


    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterWebHtmlView.__name__}")

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
    An optimized web view that requires authentication and is never cached.

    This class combines two critical behaviors for secure and dynamic web applications:

    1. **Authentication Enforcement**: Inherits from `SmarterAuthenticatedWebView`, which applies the
       `@login_required` decorator to the `dispatch` method. This ensures that only authenticated users
       can access the view. If an unauthenticated user attempts access, they are redirected to the login page,
       and the cache is expired to prevent sensitive data leakage.

    2. **Cache Prevention**: Uses the `@never_cache` decorator (applied via `method_decorator` to the
       `dispatch` method). This instructs Django and downstream proxies/browsers to never cache responses
       from this view. This is essential for views that display user-specific or sensitive information,
       ensuring that no part of the response is stored or reused.

    By combining these decorators, `SmarterAuthenticatedNeverCachedWebView` guarantees that:
    - Only logged-in users can access the view.
    - Every response is generated fresh for each request, with no caching at any layer.

    This makes it ideal for pages displaying private, frequently changing, or security-sensitive data.
    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterNeverCachedWebView.__name__}")


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedWebView(SmarterWebHtmlView):
    """
    An optimized view that requires authentication.

    This class uses the `@login_required` decorator, applied via Django's `method_decorator` to the `dispatch` method.
    The `@login_required` decorator ensures that only authenticated users can access any HTTP method (GET, POST, etc.)
    on this view. If an unauthenticated user attempts to access the view, they are redirected to the login page.
    Additionally, the `dispatch` method is overridden to expire any cache for anonymous users, further protecting
    sensitive data from being stored or leaked.

    By inheriting from both Django's ``View`` and the custom ``SmarterRequestMixin``, it
    ensures consistent request handling and integration with Smarter-specific request features.

    The view also includes helpers for retrieving the account and user profile associated with the request,
    and will force a 404 response for users who do not have a valid profile, ensuring that only properly
    provisioned users can access protected resources.

    By enforcing authentication at the dispatch level, this view provides a robust foundation for building
    secure, user-specific pages in the Smarter platform.

    This combination makes the view ideal for admin pages that display sensitive or frequently changing data, ensuring
    both strict access control and cache prevention.

    Bug Fix:

        Fixed a bug where Django method decorators were raising exceptions for unauthenticated
        users instead of redirecting them to the login page. Replaced the decorators
        with explicit checks in the `dispatch` method.

    .. versionadded:: v0.13.39
    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterAuthenticatedWebView.__name__}")

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
        verbose_logger.debug(
            "%s.setup() called with request: %s, args: %s, kwargs: %s, user: %s",
            self.logger_prefix,
            request,
            args,
            kwargs,
            getattr(request, "user", None),
        )
        # This flag is used to circumvent DRF token authentication for the brokered
        # request we make to our own API views in get_brokered_json_response().
        # We initialize it now, to ensure that it's present for any downstream
        # code that might check it before we get to dispatch().
        request = self.set_is_internal_api_request(request, False)

        retval = super().setup(request, *args, **kwargs)
        if not self.smarter_request:
            self.smarter_request = request
        return retval

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Dispatch the request, redirecting to login if the user is anonymous.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :return: An HttpResponse object.
        :rtype: HttpResponse
        """
        verbose_logger.debug(
            "%s.dispatch() called with request: %s, user: %s, args: %s, kwargs: %s",
            self.logger_prefix,
            request,
            getattr(request, "user", None),
            args,
            kwargs,
        )
        if hasattr(request, "user") and hasattr(request.user, "is_authenticated") and request.user.is_authenticated:
            response = super().dispatch(request, *args, **kwargs)
            patch_vary_headers(response, ["Cookie"])
            if not self.smarter_request:
                self.smarter_request = request
            return response

        return redirect_and_expire_cache(path="/login/")


@method_decorator(cache_control(max_age=smarter_settings.cache_expiration), name="dispatch")
@method_decorator(cache_page(smarter_settings.cache_expiration), name="dispatch")
class SmarterAuthenticatedCachedWebView(SmarterAuthenticatedWebView):
    """
    An optimized and cached web view that requires authentication.

    This class uses two important Django decorators, both applied via `method_decorator` to the `dispatch` method:

    1. **@cache_control**: Sets HTTP cache headers on responses from this view, specifying the maximum age for cached content.
       This instructs browsers and proxies to cache the response for a defined period, improving performance for repeat visits.

    2. **@cache_page**: Enables full-page caching at the Django view level, storing rendered responses in the cache backend.
       This dramatically reduces server load and speeds up response times for authenticated users accessing the same content.

    Both decorators work together to ensure that authenticated users receive cached content when appropriate, while still
    enforcing authentication via the parent class (`SmarterAuthenticatedWebView`), which uses the `@login_required` decorator.

    This view is ideal for pages where content is user-specific but does not change frequently, allowing for efficient caching
    without compromising security. The dispatch method also patches vary headers to ensure proper cache differentiation based
    on cookies, further protecting user data.
    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterAuthenticatedCachedWebView.__name__}")

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
    """
    An optimized web view that requires authentication and is never cached.

    This class uses two key Django decorators, both applied via `method_decorator` to the `dispatch` method:

    1. **@login_required** (inherited from `SmarterAuthenticatedWebView`): Ensures that only authenticated users can access any HTTP method (GET, POST, etc.) on this view. If an unauthenticated user attempts access, they are redirected to the login page and the cache is expired to prevent sensitive data leakage.

    2. **@never_cache**: Explicitly instructs browsers, proxies, and Django itself to never cache responses from this view. This is critical for views that display user-specific or sensitive information, ensuring that no part of the response is stored or reused.

    By combining these decorators, this view guarantees that:
    - Only logged-in users can access the view.
    - Every response is generated fresh for each request, with no caching at any layer.

    This makes it ideal for pages displaying private, frequently changing, or security-sensitive data, where both authentication and cache prevention are essential.
    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterAuthenticatedNeverCachedWebView.__name__}")


class SmarterAdminWebView(SmarterAuthenticatedNeverCachedWebView):
    """
    An admin-only optimized web view that is never cached.

    This class uses the `@staff_member_required` decorator, applied via Django's `method_decorator` to the `dispatch` method.
    The `@staff_member_required` decorator ensures that only users who are marked as staff in Django's authentication system
    can access any HTTP method (GET, POST, etc.) on this view. Non-staff users are redirected to the admin login page.

    In addition, this view inherits from `SmarterAuthenticatedNeverCachedWebView`, which itself applies both the
    `@login_required` and `@never_cache` decorators. This means:
    - Only authenticated staff members can access the view.
    - Every response is generated fresh for each request, with no caching at any layer.

    This combination makes the view ideal for admin pages that display sensitive or frequently changing data, ensuring
    both strict access control and cache prevention.

    Bug Fix:

        Fixed a bug where Django method decorators were raising exceptions for unauthenticated
        users instead of redirecting them to the login page. Replaced the decorators
        with explicit checks in the `dispatch` method.
    """

    @property
    def logger_prefix(self):
        return formatted_text(f"{__name__}.{SmarterAdminWebView.__name__}")

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        # Enforce login_required
        user = getattr(request, "user", None)
        if not (user and getattr(user, "is_authenticated", False)):
            return redirect_and_expire_cache(path="/login/")

        # Enforce staff_member_required
        if not getattr(user, "is_staff", False):
            # Redirect to admin login page for non-staff users
            return redirect_and_expire_cache(path="/admin/login/?next=" + request.path)

        response = super().dispatch(request, *args, **kwargs)
        patch_vary_headers(response, ["Cookie"])
        return response
