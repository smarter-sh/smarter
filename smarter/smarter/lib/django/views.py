"""Django template and view helper functions."""

import re
from collections.abc import Callable
from functools import wraps
from http import HTTPStatus
from typing import Optional, Union

from cache_results import lazy_cache
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from django.utils.html import strip_spaces_between_tags
from django.views import View
from django.views.decorators.cache import cache_control, cache_page, never_cache

from smarter.apps.account.models import User
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.throttling import throttle_wait
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.typing import SmarterDictType


# pylint: disable=W0613
def should_log(level: int) -> bool:
    """
    Check if logging should be done based on the waffle switch.

    :param level: The log level of the message. It is ignored: the switch turns every level on or off.
    :returns: True if the ``VIEW_LOGGING`` waffle switch is active.
    """
    return waffle.switch_is_active(SmarterWaffleSwitches.VIEW_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->")
"""Matches an html comment, for :meth:`SmarterView.remove_comments`."""

logger_prefix = SmarterFormattedText.text(__name__)
cache_prefix = f"{__name__}.smarter_cache_page_by_user"


def redirect_and_expire_cache(path: str = "/") -> HttpResponseRedirect:
    """
    Redirect to the given path, with headers that tell browsers and proxies not to cache the redirect.

    :param path: The path to redirect to.
    :returns: The redirect response.
    """
    response = redirect(path)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def smarter_cache_page_by_user(timeout: int) -> Callable[[Callable], Callable]:
    """
    Decorator to cache a view's response based on the authenticated user.

    This decorator applies Django's ``cache_page`` decorator with a cache key
    that is unique to each user. Authenticated users will have their
    responses cached separately, while anonymous users will share a single
    cache entry. Caching is skipped unless the ``ENABLE_SMARTER_PAGE_CACHING``
    waffle switch is active. The decorated view has an ``invalidate(request)``
    function that deletes the request's cache entry.

    Example:

    .. code-block:: python

        @method_decorator(smarter_cache_page_by_user(60 * 15), name="dispatch")
        class MyView(SmarterAuthenticatedWebView):
            ...

    :param timeout: The cache timeout in seconds.
    :returns: A decorator that can be applied to a Django view function or method.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_SMARTER_PAGE_CACHING):
                return view_func(request, *args, **kwargs)
            path = str(request.path).replace("/", ".").strip(".")
            if hasattr(request, "user") and isinstance(request.user, User) and request.user.is_authenticated:
                key_prefix = f"{cache_prefix}.user_{request.user.id}.{path}"  # type: ignore[union-attr]
            else:
                key_prefix = f"{cache_prefix}.user_anon.{path}"
            return cache_page(timeout, key_prefix=key_prefix)(view_func)(request, *args, **kwargs)

        def invalidate(request: HttpRequest, *args, **kwargs):
            if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_SMARTER_PAGE_CACHING):
                return
            if request:
                path = str(request.path).replace("/", ".").strip(".")
                if hasattr(request, "user") and isinstance(request.user, User) and request.user.is_authenticated:
                    key_prefix = f"{cache_prefix}.user_{request.user.id}.{path}"  # type: ignore[union-attr]
                else:
                    key_prefix = f"{cache_prefix}.user_anon.{path}"
                hit = lazy_cache.get(key_prefix)
                if hit is not None:
                    lazy_cache.delete(key_prefix)
                    logger.info(
                        "%s.smarter_cache_page_by_user.invalidate() cache invalidated for key_prefix: %s",
                        logger_prefix,
                        key_prefix,
                    )

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


# ------------------------------------------------------------------------------
# Web Views
# ------------------------------------------------------------------------------
class SmarterView(View):
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

    _ready: bool = False
    template_path: str = ""
    context: SmarterDictType = {}

    @property
    def formatted_class_name(self) -> str:
        """
        Return the class name in a formatted string along with the name of this view.

        :returns: The dotted name of this view class and its instance id, formatted for logs.
        """
        class_name = f"{__name__}.{SmarterView.__name__}[{id(self)}]"
        return logging.SmarterFormattedText.text(class_name)

    @property
    def ready(self) -> bool:
        """
        Return True if the view is ready to handle requests, False otherwise.

        This can be used to check if the necessary context or data is available before processing a request.

        :returns: True if the view is ready.
        """
        return self._ready

    def remove_comments(self, html: str) -> str:
        """
        Remove HTML comments from an html string.

        :param html: The HTML string from which to remove comments.
        :returns: The HTML string without comments.
        """
        return HTML_COMMENT_PATTERN.sub("", html)

    def minify_html(self, html: str) -> str:
        """
        Minify an html string, by removing the whitespace between tags.

        It is one regular expression, not a parse: :class:`~smarter.lib.django.middleware.html_minify.HTMLMinifyMiddleware`
        parses every html response anyway.

        :param html: The HTML string to minify.
        :returns: The minified HTML string.
        """
        minified_html = strip_spaces_between_tags(html)
        return minified_html

    def render_clean_html(
        self, request: HttpRequest, template_path: str, context: Optional[SmarterDictType] = None
    ) -> Union[str, HttpResponse]:
        """
        Render a template as a string, with comments removed and minified.

        :param request: The HTTP request object.
        :param template_path: The path to the template to render.
        :param context: The context to use for rendering the template, or the view's context if None or empty.
        :returns: The rendered, cleaned HTML string, or a 500 response if the template could not be rendered.
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
                request.build_absolute_uri(),
                template_path,
                e,
                exc_info=True,
            )
            return HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)

        html = response.content.decode(response.charset)
        html_no_comments = self.remove_comments(html=html)
        minified_html = self.minify_html(html=html_no_comments)
        return minified_html


class SmarterWebXmlView(SmarterView):
    """Base view for smarter xml web views."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Render ``template_path`` with the view's context.

        :param request: The request.
        :returns: The rendered response.
        """
        return render(request=request, template_name=self.template_path, context=self.context)

    @property
    def formatted_class_name(self) -> str:
        """
        Return the class name in a formatted string along with the name of this view.

        :returns: The dotted name of this view class and its instance id, formatted for logs.
        """
        class_name = f"{__name__}.{SmarterWebXmlView.__name__}[{id(self)}]"
        return logging.SmarterFormattedText.text(class_name)


class SmarterWebTxtView(SmarterView):
    """Base view for smarter text web views."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Render ``template_path`` without comments and minified, as ``text/plain``.

        :param request: The request.
        :returns: The text response, or a 500 response if rendering failed.
        """
        minified_html = self.render_clean_html(request, template_path=self.template_path, context=self.context)
        if isinstance(minified_html, HttpResponse):
            return minified_html
        return HttpResponse(content=minified_html, content_type="text/plain")

    @property
    def formatted_class_name(self) -> str:
        """
        Return the class name in a formatted string along with the name of this view.

        :returns: The dotted name of this view class and its instance id, formatted for logs.
        """
        class_name = f"{__name__}.{SmarterWebTxtView.__name__}[{id(self)}]"
        return logging.SmarterFormattedText.text(class_name)


class SmarterWebHtmlView(SmarterView):
    """
    Base view for smarter web views.

    Includes helpers for rendering, minifying and stripping out developer comments.
    """

    @property
    def formatted_class_name(self) -> str:
        """
        Return the class name in a formatted string along with the name of this view.

        :returns: The dotted name of this view class and its instance id, formatted for logs.
        """
        class_name = f"{__name__}.{SmarterWebHtmlView.__name__}[{id(self)}]"
        return logging.SmarterFormattedText.text(class_name)

    # pylint: disable=W0613
    def clean_http_response(
        self,
        request: HttpRequest,
        template_path: str,
        *args,
        context: Optional[SmarterDictType] = None,
        **kwargs,
    ) -> HttpResponse:
        """
        Render a template and return an HttpResponse with comments removed.

        :param request: The HTTP request object.
        :param template_path: The path to the template to render.
        :param args: Ignored.
        :param context: The context to use for rendering the template.
        :param kwargs: Ignored.
        :returns: An HttpResponse with the cleaned HTML content, or the error response of
            :meth:`render_clean_html` if the template could not be rendered.
        """
        minified_html = self.render_clean_html(request, template_path, context)
        if isinstance(minified_html, HttpResponse):
            # an error response. Wrapping it would turn a 500 into a 200 whose body is its repr.
            return minified_html
        return HttpResponse(content=minified_html, content_type="text/html")

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests and return a cleaned HttpResponse.

        A view without a template, e.g. a JSON api that only answers POST, has nothing to render, so
        a GET receives 405 Method Not Allowed instead of a 500 (issue #963).

        :param request: The HTTP request object.
        :param args: Passed to :meth:`clean_http_response`.
        :param kwargs: Passed to :meth:`clean_http_response`.
        :returns: An HttpResponse with the cleaned HTML content, or a 405 response when the view
            has no template.
        """
        if not self.template_path:
            return self.get_not_allowed(request, *args, **kwargs)
        return self.clean_http_response(request, self.template_path, *args, context=self.context, **kwargs)

    def get_not_allowed(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Answer a GET to a view that has no template with 405 Method Not Allowed.

        Django's own :meth:`http_method_not_allowed` never runs for these views, because this class
        defines :meth:`get`. Its ``Allow`` header would list GET and HEAD, so they are removed.

        :param request: The HTTP request object.
        :param args: Passed to :meth:`http_method_not_allowed`.
        :param kwargs: Passed to :meth:`http_method_not_allowed`.
        :returns: A 405 response whose ``Allow`` header lists the methods that the view handles.
        """
        response = self.http_method_not_allowed(request, *args, **kwargs)
        allowed_methods = []
        # Django's View._allowed_methods(), which django-stubs doesn't declare
        for method_name in self.http_method_names:
            method = method_name.upper()
            if hasattr(self, method_name) and method not in ("GET", "HEAD"):
                allowed_methods.append(method)
        response["Allow"] = ", ".join(allowed_methods)
        return response


@method_decorator(never_cache, name="dispatch")
class SmarterNeverCachedWebView(SmarterWebHtmlView):
    """
    A web view that is never cached, and does not require authentication.

    It extends :class:`SmarterWebHtmlView`, not :class:`SmarterAuthenticatedWebView`, so anonymous
    users can access it: it neither requires login nor initializes ``SmarterRequestMixin``. For a page
    that must be both private and never cached, use :class:`SmarterAuthenticatedNeverCachedWebView`.

    The ``@never_cache`` decorator, applied via ``method_decorator`` to the ``dispatch`` method,
    instructs Django and downstream proxies and browsers to never cache responses from this view,
    so every response is generated fresh for each request.
    """

    @property
    def formatted_class_name(self) -> str:
        """
        Return the class name in a formatted string along with the name of this view.

        :returns: The dotted name of this view class and its instance id, formatted for logs.
        """
        class_name = f"{__name__}.{SmarterNeverCachedWebView.__name__}[{id(self)}]"
        return logging.SmarterFormattedText.text(class_name)


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedWebView(SmarterWebHtmlView, SmarterRequestMixin):
    """
    An optimized view that requires authentication.

    Only authenticated users can access any HTTP method (GET, POST, etc.) on this view. Its ``dispatch``
    method checks ``request.user.is_authenticated`` explicitly, and redirects an anonymous user to the
    login page with a response that expires the cache, so that sensitive data is not stored or leaked.
    The class is also decorated with ``@login_required``, but the explicit check in ``dispatch`` is what
    redirects, rather than raising, for an unauthenticated user.

    By inheriting from both Django's ``View`` and the custom ``SmarterRequestMixin``, it
    ensures consistent request handling and integration with Smarter-specific request features.

    The view also includes helpers for retrieving the account and user profile associated with the request,
    and will force a 404 response for users who do not have a valid profile, ensuring that only properly
    provisioned users can access protected resources.

    By enforcing authentication at the dispatch level, this view provides a robust foundation for building
    secure, user-specific pages in the Smarter platform.

    Successful responses vary on the ``Cookie`` header.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        SmarterRequestMixin.__init__(self, **kwargs)

    @property
    def formatted_class_name(self) -> str:
        """
        Return the class name in a formatted string along with the name of this view.

        :returns: The dotted name of this view class and its instance id, formatted for logs.
        """
        class_name = f"{__name__}.{SmarterAuthenticatedWebView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def log_ready_status(self) -> None:
        """
        Log the ready status of the view at DEBUG, building the message only when it will be logged.

        :returns: None.
        """
        if logger.should_log(logging.DEBUG):
            logger.debug("%s.log_ready_status() is %s", self.formatted_class_name, self.ready_state)

    def setup(self, request: HttpRequest, *args, **kwargs) -> None:
        """
        Set up the view with the request and any additional arguments.

        This method initializes the SmarterRequestMixin with the request, and marks the request as
        not an internal api request.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        """
        user = getattr(request, "user", None)
        # This flag is used to circumvent DRF token authentication for the brokered
        # request we make to our own API views in get_brokered_json_response().
        # We initialize it now, to ensure that it's present for any downstream
        # code that might check it before we get to dispatch().
        request = self.set_is_internal_api_request(request, False)
        super().setup(request, *args, **kwargs)
        if isinstance(user, AnonymousUser):
            user = None
        SmarterRequestMixin.smarter_request_setup(self, *args, request=request, user=user, **kwargs)
        if super().ready:
            self._ready = True
        self.log_ready_status()

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        """
        Dispatch the request, redirecting to login if the user is anonymous.

        :param request: The HTTP request object.
        :param args: Passed to the view.
        :param kwargs: Passed to the view.
        :returns: The view's response, which varies on ``Cookie``, or a redirect to ``/login/`` that
            expires the cache.
        """
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

    This class uses two important Django decorators, both applied via ``method_decorator`` to the ``dispatch`` method:

    1. **@cache_control**: Sets HTTP cache headers on responses from this view, specifying the maximum age for cached content.
       This instructs browsers and proxies to cache the response for a defined period, improving performance for repeat visits.

    2. **@cache_page**: Enables full-page caching at the Django view level, storing rendered responses in the cache backend.
       This dramatically reduces server load and speeds up response times for authenticated users accessing the same content.

    Both decorators work together to ensure that authenticated users receive cached content when appropriate, while still
    enforcing authentication via the parent class (:class:`SmarterAuthenticatedWebView`).

    This view is ideal for pages where content is user-specific but does not change frequently, allowing for efficient caching
    without compromising security. The dispatch method also patches vary headers to ensure proper cache differentiation based
    on cookies, further protecting user data.
    """

    def log_ready_status(self) -> None:
        """
        Log the ready status of the view at INFO, building the message only when it will be logged.

        :returns: None.
        """
        if logger.should_log(logging.INFO):
            logger.info("%s.log_ready_status() is %s", self.formatted_class_name, self.ready_state)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        """
        Dispatch the request and patch vary headers for successful responses.

        :param request: The HTTP request object.
        :param args: Passed to the view.
        :param kwargs: Passed to the view.
        :returns: The view's response, which varies on ``Cookie`` if its status is below 300.
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

    It combines two behaviors:

    1. **Authentication** (inherited from :class:`SmarterAuthenticatedWebView`): Ensures that only authenticated users can access any HTTP method (GET, POST, etc.) on this view. If an unauthenticated user attempts access, they are redirected to the login page and the cache is expired to prevent sensitive data leakage.

    2. **@never_cache**, applied via ``method_decorator`` to the ``dispatch`` method: Explicitly instructs browsers, proxies, and Django itself to never cache responses from this view. This is critical for views that display user-specific or sensitive information, ensuring that no part of the response is stored or reused.

    Together, they guarantee that:

    - Only logged-in users can access the view.
    - Every response is generated fresh for each request, with no caching at any layer.

    This makes it ideal for pages displaying private, frequently changing, or security-sensitive data, where both authentication and cache prevention are essential.
    """


class SmarterAdminWebView(SmarterAuthenticatedNeverCachedWebView):
    """
    An admin-only optimized web view that is never cached.

    Its ``dispatch`` method checks the user explicitly, rather than with a decorator such as
    ``@staff_member_required``, so that a user who may not access the view is redirected rather than
    shown an error:

    - An anonymous user is redirected to ``/login/``.
    - An authenticated user who is not marked as staff (``is_staff``) is redirected to the admin login page.

    Both redirects expire the cache. In addition, this view inherits from
    :class:`SmarterAuthenticatedNeverCachedWebView`, which is never cached. This means:

    - Only authenticated staff members can access the view.
    - Every response is generated fresh for each request, with no caching at any layer.

    This combination makes the view ideal for admin pages that display sensitive or frequently changing data, ensuring
    both strict access control and cache prevention.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        """
        Redirect anonymous users to the login page and non-staff users to the admin login, then dispatch.

        The response varies on the ``Cookie`` header.

        :param request: The request.
        :param args: Passed to the view.
        :param kwargs: Passed to the view.
        :returns: The view's response, or a redirect that expires the cache.
        """
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


@method_decorator(never_cache, name="dispatch")
class SmarterOptionallyAuthenticatedApiView(SmarterView, SmarterRequestMixin):
    """
    A JSON api view whose clients may or may not be authenticated, and which is never cached.

    The web console's views, e.g. :class:`SmarterAuthenticatedWebView`, serve pages to logged-in users,
    and redirect everyone else to the login page. This view is for the apis that a deployed LLMClient
    serves to browsers and api clients that are not web console users, e.g. the configuration and
    prompt apis of a page that embeds Smarter Chat: it never redirects, and leaves authorization to the
    subclass, which knows the resource. A subclass decides, in its ``dispatch()``, whether the request
    may proceed, typically with :attr:`is_authenticated`, and answers with a JSON error if not.

    - **No login redirect.** An anonymous request reaches the subclass's ``dispatch()``.
    - **CSRF exempt.** Its clients send api keys or no credentials, not the web console's session.
    - **Never cached**, and responses vary by ``Cookie``, so that one client's data is never served to another.
    - **Rate limited**, as Django REST Framework views are, by :func:`smarter.lib.drf.throttling.throttle_wait`:
      per user if authenticated, otherwise per IP address. A throttled request receives
      :meth:`throttled_response`, before the subclass's handler runs.

    It initializes :class:`~smarter.lib.django.request.SmarterRequestMixin` with the request, as
    :class:`SmarterAuthenticatedWebView` does, so the request's account, user and user profile are set
    for an authenticated request, and empty for an anonymous one.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        SmarterRequestMixin.__init__(self, **kwargs)
        self._throttle_checked: bool = False
        """Whether :meth:`throttle` has checked this request against its rate limits."""
        self._throttle_wait: Optional[int] = None
        """The seconds to wait before retrying, from the check, or None if the request isn't throttled."""

    @classmethod
    def as_view(cls, **initkwargs):
        """
        The view function, CSRF exempt.

        The exemption is set here, as Django REST Framework's ``APIView`` does, rather than with
        ``@method_decorator(csrf_exempt, name="dispatch")``, because Django copies it from the most
        derived ``dispatch()``, so a subclass that overrides ``dispatch()`` would lose it.

        :param initkwargs: The view's class attributes to override, as for ``View.as_view()``.
        :returns: The view function.
        """
        view = super().as_view(**initkwargs)
        view.csrf_exempt = True  # type: ignore[attr-defined]
        return view

    @property
    def formatted_class_name(self) -> str:
        """
        Return the class name in a formatted string along with the name of this view.

        :returns: The dotted name of this view class and its instance id, formatted for logs.
        """
        class_name = f"{__name__}.{SmarterOptionallyAuthenticatedApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def is_authenticated(self) -> bool:
        """
        Whether the request is authenticated, by the web console's session or by an api key.

        :returns: True for an authenticated user.
        """
        user = getattr(self.smarter_request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False))

    def setup(self, request: HttpRequest, *args, **kwargs) -> None:
        """
        Set up the view with the request, and initialize SmarterRequestMixin with it.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        """
        user = getattr(request, "user", None)
        request = self.set_is_internal_api_request(request, False)
        super().setup(request, *args, **kwargs)
        if isinstance(user, AnonymousUser):
            user = None
        SmarterRequestMixin.smarter_request_setup(self, *args, request=request, user=user, **kwargs)
        if not self.smarter_request:
            self.smarter_request = request

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        """
        Dispatch the request, authenticated or not, and vary the response by ``Cookie``.

        :param request: The HTTP request object.
        :param args: Passed to the view.
        :param kwargs: Passed to the view.
        :returns: The view's response, or :meth:`throttled_response` if the request was throttled.
        """
        response: Optional[HttpResponseBase] = self.throttle(request)
        if response is None:
            response = super().dispatch(request, *args, **kwargs)
        patch_vary_headers(response, ["Cookie"])
        return response

    def throttle(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Check the request against its rate limits, once.

        :meth:`dispatch` calls it before the handler runs. A subclass whose ``dispatch()`` does costly
        work before it calls ``super().dispatch()``, e.g. queries or creating rows, calls it first, so
        that a throttled request does none of it. The request is counted once however often it is
        called, since every check counts against the limits.

        :param request: The HTTP request object.
        :returns: :meth:`throttled_response` if the request exceeded its rate limit, otherwise None.
        """
        if not self._throttle_checked:
            self._throttle_wait = throttle_wait(request, self)
            self._throttle_checked = True
        if self._throttle_wait is None:
            return None
        response = self.throttled_response(request, self._throttle_wait)
        patch_vary_headers(response, ["Cookie"])
        return response

    # pylint: disable=unused-argument
    def throttled_response(self, request: HttpRequest, wait: int) -> HttpResponse:
        """
        Return the response to a request that exceeded its rate limit.

        :param request: The HTTP request object.
        :param wait: The number of seconds to wait before retrying.
        :returns: HTTP 429 Too Many Requests, with a ``Retry-After`` header.
        """
        response = JsonResponse(
            {"detail": f"Request was throttled. Expected available in {wait} seconds."},
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )
        response["Retry-After"] = str(wait)
        return response
