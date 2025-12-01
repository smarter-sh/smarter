"""
This module contains the SmarterCsrfViewMiddleware class, which is a subclass of Django's
SmarterCsrfViewMiddleware. It adds the ability to add the ChatBot's URL to the list of
trusted origins for CSRF protection.
"""

import logging
from collections import defaultdict
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.functional import cached_property

from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import is_authenticated_request
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import SmarterHttpResponseServerError
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


logger.info("Loading smarter.apps.chatbot.middleware.csrf.SmarterCsrfViewMiddleware")


class SmarterCsrfViewMiddleware(CsrfViewMiddleware, SmarterHelperMixin):
    """
    Middleware for enforcing CSRF (Cross-Site Request Forgery) protection with dynamic trusted origins.

    This middleware extends Django's built-in CSRF middleware to support dynamic addition of trusted
    origins, particularly for chatbot-related requests. It ensures that POST requests with a CSRF cookie
    require a valid ``csrfmiddlewaretoken``, and it sets outgoing CSRF cookies as needed.

    The middleware is designed to work seamlessly with the ``{% csrf_token %}`` template tag and
    provides additional logic for chatbot requests, health checks, and internal IP addresses. It also
    integrates with application logging and waffle switches for feature toggling.

    :cvar smarter_request: The current request wrapped in a SmarterRequestMixin, or None.
    :vartype smarter_request: Optional[SmarterRequestMixin]

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

    smarter_request: Optional[SmarterRequestMixin] = None

    @property
    def CSRF_TRUSTED_ORIGINS(self) -> list[str]:
        """
        Return the list of trusted origins for CSRF.
        If the request is for a ChatBot, the ChatBot's URL is added to the list.
        """
        retval = settings.CSRF_TRUSTED_ORIGINS
        if self.smarter_request and (self.smarter_request.is_chatbot or self.smarter_request.is_config):
            retval += [self.smarter_request.url]
        logger.info("%s.CSRF_TRUSTED_ORIGINS: %s", self.formatted_class_name, retval)
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

    def process_request(self, request):
        """
        Process the request to set up the CSRF protection.
        If the request is for a ChatBot, then we'll exempt it from CSRF checks.
        """
        host = request.get_host()
        if not host:
            return SmarterHttpResponseServerError(
                request=request,
                error_message="Internal error (500) - could not parse request.",
            )

        # Short-circuit for health checks
        if request.path.replace("/", "") in self.amnesty_urls:
            return None

        # Short-circuit for any requests born from internal IP address hosts.
        # This is unlikely, but not impossible.
        if any(host.startswith(prefix) for prefix in settings.SMARTER_INTERNAL_IP_PREFIXES):
            logger.info(
                "%s %s identified as an internal IP address, exiting.",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request),
            )
            return None

        url = self.smarter_build_absolute_uri(request)

        # this is a workaround to not being able to inherit from
        # SmarterRequestMixin inside of middleware.
        logger.info("%s.process_request - initializing SmarterRequestMixin", self.formatted_class_name)
        self.smarter_request = SmarterRequestMixin(request)
        if self.smarter_request and hasattr(self.smarter_request, "user") and self.smarter_request.user is not None:
            request.user = self.smarter_request.user

        if not is_authenticated_request(request):
            # this would only happen if the url routes to DRF but no
            # Authentication token was passed in the header. In this
            # case we'll add our own smarter admin user just for initializing
            # the ChatBotHelper.
            admin_user_profile = get_cached_smarter_admin_user_profile()
            request.user = admin_user_profile.user
            logger.debug(
                "%s: request is not (yet) authenticated. Using admin user as a proxy for evaluating CSRF_TRUSTED_ORIGINS: %s",
                self.formatted_class_name,
                admin_user_profile,
            )

        logger.info("%s.__call__(): %s", self.formatted_class_name, url)

        if self.smarter_request.is_chatbot:
            logger.info("%s ChatBot: %s is csrf exempt.", self.formatted_class_name, url)
            return None

        if self.smarter_request.is_chatbot:
            logger.info("%s.process_request(): csrf_middleware_logging is active", self.formatted_class_name)
            logger.info("=" * 80)
            logger.info("%s ChatBot: %s", self.formatted_class_name, url)
            for cookie in request.COOKIES:
                logger.info("SmarterCsrfViewMiddleware request.COOKIES: %s", cookie)
            logger.info("%s cookie settings", self.formatted_class_name)
            logger.info("%s settings.CSRF_COOKIE_NAME: %s", self.formatted_class_name, settings.CSRF_COOKIE_NAME)
            logger.info(
                "%s request.META['CSRF_COOKIE']: %s", self.formatted_class_name, request.META.get("CSRF_COOKIE")
            )
            logger.info("%s settings.CSRF_COOKIE_AGE: %s", self.formatted_class_name, settings.CSRF_COOKIE_AGE)
            logger.info("%s settings.CSRF_COOKIE_DOMAIN: %s", self.formatted_class_name, settings.CSRF_COOKIE_DOMAIN)
            logger.info("%s settings.CSRF_COOKIE_PATH: %s", self.formatted_class_name, settings.CSRF_COOKIE_PATH)
            logger.info("%s settings.CSRF_COOKIE_SECURE: %s", self.formatted_class_name, settings.CSRF_COOKIE_SECURE)
            logger.info(
                "%s settings.CSRF_COOKIE_HTTPONLY: %s", self.formatted_class_name, settings.CSRF_COOKIE_HTTPONLY
            )
            logger.info(
                "%s settings.CSRF_COOKIE_SAMESITE: %s", self.formatted_class_name, settings.CSRF_COOKIE_SAMESITE
            )
            logger.info("=" * 80)

        # ------------------------------------------------------
        return super().process_request(request)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if smarter_settings.environment == "local":
            logger.debug("%s._accept: environment is local. ignoring csrf checks", self.formatted_class_name)
            return None
        if (
            self.smarter_request
            and self.smarter_request.is_chatbot
            and waffle.switch_is_active(SmarterWaffleSwitches.CSRF_SUPPRESS_FOR_CHATBOTS)
        ):
            logger.info(
                "%s.process_view() %s waffle switch is active",
                self.formatted_class_name,
                SmarterWaffleSwitches.CSRF_SUPPRESS_FOR_CHATBOTS,
            )
            return None
        response = super().process_view(request, callback, callback_args, callback_kwargs)
        if isinstance(response, HttpResponseForbidden):
            logger.error("%s CSRF validation failed", self.formatted_class_name)
        return response
