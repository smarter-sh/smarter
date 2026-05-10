"""
This module contains the SmarterCsrfViewMiddleware class, which is a subclass of Django's
SmarterCsrfViewMiddleware. It adds the ability to add the ChatBot's URL to the list of
trusted origins for CSRF protection.
"""

import inspect
from collections import defaultdict
from urllib.parse import urlparse

from asgiref.sync import markcoroutinefunction
from django.conf import settings
from django.http import HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.functional import cached_property

from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import SmarterHttpResponseServerError
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])


logger.debug("Loading %s", formatted_text(__name__ + ".SmarterCsrfViewMiddleware"))


class SmarterCsrfViewMiddleware(CsrfViewMiddleware, SmarterRequestMixin):
    """
    Middleware for enforcing CSRF (Cross-Site Request Forgery) protection with dynamic trusted origins.

    This middleware extends Django's built-in CSRF middleware to support dynamic addition of trusted
    origins, particularly for chatbot-related requests. It ensures that POST requests with a CSRF cookie
    require a valid ``csrfmiddlewaretoken``, and it sets outgoing CSRF cookies as needed.

    The middleware is designed to work seamlessly with the ``{% csrf_token %}`` template tag and
    provides additional logic for chatbot requests, health checks, and internal IP addresses. It also
    integrates with application logging and waffle switches for feature toggling.

    Note that this middleware uses the admin user as a proxy for initializing the SmarterRequestMixin,
    which is used solely for purposes of determining if the request is for a ChatBot. The user
    object is stripped from the request before passing it downstream in the middleware chain.

    **Key Features**

    - Dynamically adds chatbot URLs to the list of CSRF trusted origins.
    - Exempts chatbot requests from CSRF checks when appropriate.
    - Handles health check endpoints and internal IP addresses efficiently.
    - Provides detailed logging for CSRF-related events and decisions.
    - Integrates with Django's CSRF protection and application-specific settings.

    .. note::
        - Chatbot requests can be exempted from CSRF checks based on waffle switches.
        - Trusted origins are dynamically extended for chatbot and config requests.
        - Logging is controlled via a waffle switch and the application's log level.

    **Example**

    To enable this middleware, add it to your Django project's middleware settings::

        MIDDLEWARE = [
            ...
            'smarter.lib.django.middleware.csrf.SmarterCsrfViewMiddleware',
            ...
        ]

    :param request: The incoming HTTP request object.
    :type request: django.http.HttpRequest

    :returns: The HTTP response object, or None if the request is exempted from CSRF checks.
    :rtype: django.http.HttpResponse or None
    """

    sync_capable = True
    async_capable = True

    _ready: bool = False

    def __init__(self, get_response, *args, **kwargs):
        """
        Initialize the SmarterCsrfViewMiddleware.

        We are not yet authenticated, which is fine. we use the admin user for
        any needed context. This is needed for evaluating whether or not this
        request is for a ChatBot.
        """
        logger.debug("%s.__init__() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        super().__init__(get_response, *args, **kwargs)
        self.is_async = inspect.iscoroutinefunction(get_response)
        if self.is_async:
            markcoroutinefunction(self)

        admin_user_profile = None
        # this can happen on fresh installations where migrations have not yet run.
        if self.is_async:
            SmarterRequestMixin.__init__(self, get_response, *args, **kwargs)
            logger.warning(
                "%s.__init__() could not get admin user profile because we're in an async context. SmarterRequestMixin initialized without user context. This may cause issues with ChatBot requests.",
                self.formatted_class_name,
            )
        else:
            try:
                admin_user_profile = get_cached_smarter_admin_user_profile()
                SmarterRequestMixin.__init__(
                    self,
                    get_response,
                    request=None,
                    user=admin_user_profile.user,
                    user_profile=admin_user_profile,
                    account=admin_user_profile.account,
                    *args,
                    **kwargs,
                )
                self._ready = True
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("%s.__init__() could not get admin user profile: %s", self.formatted_class_name, str(e))
                SmarterRequestMixin.__init__(self, get_response, *args, **kwargs)

    @property
    def ready(self) -> bool:
        """
        Return whether the middleware is ready for use. The middleware is considered ready
        if it has been properly initialized with the admin user profile.
        """
        return self._ready

    @property
    def formatted_class_name(self) -> str:
        """Return the formatted class name for logging purposes."""
        return formatted_text(f"{__name__}.{SmarterCsrfViewMiddleware.__name__}")

    @property
    def CSRF_TRUSTED_ORIGINS(self) -> list[str]:
        """
        Return the list of trusted origins for CSRF.
        If the request is for a ChatBot, the ChatBot's URL is added to the list.
        """
        retval = settings.CSRF_TRUSTED_ORIGINS
        if self.is_chatbot or self.is_config:
            retval += [self.url]
        logger.debug("%s.CSRF_TRUSTED_ORIGINS: %s", self.formatted_class_name, retval)
        return retval

    @cached_property
    def csrf_trusted_origins_hosts(self):
        return [urlparse(origin).netloc.lstrip("*") for origin in self.CSRF_TRUSTED_ORIGINS]

    @cached_property
    def allowed_origins_exact(self):
        return {origin for origin in self.CSRF_TRUSTED_ORIGINS if "*" not in origin}

    @cached_property
    def allowed_origin_subdomains(self):
        """
        A mapping of allowed schemes to list of allowed netlocs, where all
        subdomains of the netloc are allowed.
        """
        allowed_origin_subdomains = defaultdict(list)
        for parsed in (urlparse(origin) for origin in self.CSRF_TRUSTED_ORIGINS if "*" in origin):
            allowed_origin_subdomains[parsed.scheme].append(parsed.netloc.lstrip("*"))
        return allowed_origin_subdomains

    def __call__(self, request):
        """
        New-style middleware entrypoint for CSRF protection with dynamic trusted origins and chatbot logic.
        """
        host = request.get_host()

        if not host:
            return SmarterHttpResponseServerError(
                request=request,
                error_message="Internal error (500) - could not parse request.",
            )

        # Short-circuit for health checks
        if request.path.replace("/", "") in self.amnesty_urls:
            return self.get_response(request)

        # Short-circuit for any requests born from internal IP address hosts.
        if any(host.startswith(prefix) for prefix in smarter_settings.internal_ip_prefixes):
            logger.debug(
                "%s.__call__() %s identified as an internal IP address, exiting.",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request),
            )
            return self.get_response(request)

        logger.debug(
            "%s.__call__ url=%s user=%s",
            self.formatted_class_name,
            self.url,
            request.user if hasattr(request, "user") and hasattr(request.user, "is_authenticated") else "N/A",
        )

        # Local/dev bypass
        if smarter_settings.environment == SmarterEnvironments.LOCAL:
            logger.debug("%s.__call__(): environment is local. ignoring csrf checks", self.formatted_class_name)
            return self.get_response(request)

        # Chatbot bypass
        if self.is_chatbot and waffle.switch_is_active(SmarterWaffleSwitches.CSRF_SUPPRESS_FOR_CHATBOTS):
            logger.info(
                "%s.__call__() SmarterWaffleSwitches.CSRF_SUPPRESS_FOR_CHATBOTS is active. ignoring csrf checks for ChatBot request %s",
                self.formatted_class_name,
                self.url,
            )
            return self.get_response(request)

        # Chatbot logging
        if self.is_chatbot:
            logger.debug("%s.__call__(): csrf_middleware_logging is active", self.formatted_class_name)
            logger.debug("=" * 80)
            logger.debug("%s ChatBot: %s", self.formatted_class_name, self.url)
            for cookie in request.COOKIES:
                logger.debug("SmarterCsrfViewMiddleware request.COOKIES: %s", cookie)
            logger.debug("%s cookie settings", self.formatted_class_name)
            logger.debug("%s settings.CSRF_COOKIE_NAME: %s", self.formatted_class_name, settings.CSRF_COOKIE_NAME)
            logger.debug(
                "%s request.META['CSRF_COOKIE']: %s", self.formatted_class_name, request.META.get("CSRF_COOKIE")
            )
            logger.debug("%s settings.CSRF_COOKIE_AGE: %s", self.formatted_class_name, settings.CSRF_COOKIE_AGE)
            logger.debug("%s settings.CSRF_COOKIE_DOMAIN: %s", self.formatted_class_name, settings.CSRF_COOKIE_DOMAIN)
            logger.debug("%s settings.CSRF_COOKIE_PATH: %s", self.formatted_class_name, settings.CSRF_COOKIE_PATH)
            logger.debug("%s settings.CSRF_COOKIE_SECURE: %s", self.formatted_class_name, settings.CSRF_COOKIE_SECURE)
            logger.debug(
                "%s settings.CSRF_COOKIE_HTTPONLY: %s", self.formatted_class_name, settings.CSRF_COOKIE_HTTPONLY
            )
            logger.debug(
                "%s settings.CSRF_COOKIE_SAMESITE: %s", self.formatted_class_name, settings.CSRF_COOKIE_SAMESITE
            )
            logger.debug("=" * 80)

        # Remove user before passing downstream if present
        if hasattr(request, "user") and request.user is not None:
            setattr(request, "user", None)

        # Call parent (CsrfViewMiddleware) __call__ for CSRF logic
        response = super().__call__(request)
        if isinstance(response, HttpResponseForbidden):
            logger.error(
                "%s.__call__() CSRF validation failed | path=%s | method=%s | user_agent=%s | remote_addr=%s | origin=%s | referer=%s | csrf_cookie=%s | session_key=%s",
                self.formatted_class_name,
                request.path,
                request.method,
                request.META.get("HTTP_USER_AGENT"),
                request.META.get("REMOTE_ADDR"),
                request.META.get("HTTP_ORIGIN"),
                request.META.get("HTTP_REFERER"),
                request.COOKIES.get(settings.CSRF_COOKIE_NAME),
                getattr(request.session, "session_key", None),
            )
        return response
