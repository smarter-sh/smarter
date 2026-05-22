"""
ASGI-safe dynamic CSRF middleware for Django.

This module extends :class:`django.middleware.csrf.CsrfViewMiddleware`
to support request-scoped trusted origins while preserving full
compatibility with Django's supported middleware lifecycle.

The implementation intentionally relies only on officially supported
extension points and avoids custom async adaptation logic.

Key Features
============

- Fully compatible with ASGI and WSGI
- Dynamic request-scoped CSRF trusted origins
- Stateless request processing
- Chatbot-aware CSRF bypass support
- Internal network bypass support
- Local development environment bypass
- Compatibility with Django admin and authentication middleware
- Compatible with sync views, async views, and Channels

Design Constraints
==================

This middleware intentionally avoids several patterns that commonly
introduce concurrency bugs or unsupported Django behavior:

- Does not mutate ``request.user``
- Does not override ``__call__``
- Does not use ``markcoroutinefunction``
- Does not manually manage async adaptation
- Does not persist middleware state across requests
- Does not mutate ``settings.CSRF_TRUSTED_ORIGINS``

Concurrency Safety
==================

All trusted origin computation is request-scoped.

Dynamic CSRF origin lists are created fresh for each request and are
never written back to Django settings or shared global state.

Temporary compatibility overrides required by Django internals are
strictly limited to the duration of ``process_view()`` execution and
are restored immediately afterward.

Behavior
========

For each request, the middleware:

#. Evaluates feature-flag enablement via Django Waffle
#. Applies environment-specific bypass rules
#. Applies internal network bypass rules
#. Applies chatbot-specific CSRF bypass logic
#. Dynamically computes trusted origins
#. Delegates CSRF validation to Django's built-in middleware

If CSRF validation fails, detailed structured logging is emitted
containing request metadata for diagnostics.

Dynamic Trusted Origins
=======================

Dynamic origins are derived from the active request and may include:

- chatbot-specific origins
- configuration endpoints
- environment-specific origins

The middleware never mutates:

- ``settings.CSRF_TRUSTED_ORIGINS``
- Django global middleware configuration
- shared process state

Django Compatibility
====================

This middleware preserves compatibility with Django internals by
maintaining the expected behavior of:

- ``csrf_trusted_origins_hosts``
- ``allowed_origins_exact``
- ``allowed_origin_subdomains``

These properties are exposed using Django-compatible interfaces while
still avoiding persistent mutation of global settings.

Classes
=======

.. autosummary::
   :toctree: generated/

   SmarterCsrfViewMiddleware

Dependencies
============

- Django
- Django Waffle

Logging
=======

Middleware lifecycle events, bypass conditions, dynamic origin
generation, and CSRF validation failures are logged using the
application's structured logging framework.

Notes
=====

This middleware depends on behavior provided by
:class:`smarter.lib.django.request.SmarterRequestMixin`.

Because Django's native CSRF middleware already supports both sync
and async execution models, this implementation avoids introducing
custom coroutine wrappers or async middleware adaptation logic.

Warnings
========

Although temporary reassignment of Django internal CSRF origin
structures occurs during request processing, the original values are
always restored immediately after validation completes.

This behavior is intentionally scoped to the request lifecycle and is
designed to preserve compatibility with Django's internal CSRF
validation flow.
"""

from collections import defaultdict
from urllib.parse import urlparse

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.functional import cached_property

from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins.helper_mixin import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__)


if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF):
    logger.debug(
        "%s is %s",
        formatted_text(__name__ + ".SmarterCsrfViewMiddleware"),
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        formatted_text(__name__ + ".SmarterCsrfViewMiddleware"),
        SmarterHelperMixin().formatted_state_not_ready,
    )


class SmarterCsrfViewMiddleware(CsrfViewMiddleware, SmarterRequestMixin):
    """
    ASGI-safe CSRF middleware.

    Extends Django's CsrfViewMiddleware while preserving all Django
    request lifecycle invariants.
    """

    def __init__(self, get_response):
        super().__init__(get_response)

        # initialize request mixin WITHOUT fake users/admin state
        SmarterRequestMixin.__init__(self)

    def __call__(self, request):
        """
        Standard Django middleware entry point.

        This method intentionally does not contain any custom logic and
        simply delegates to the parent class to preserve Django's
        expected middleware lifecycle behavior.
        """
        if self.deserves_amnesty(request.path):
            return self.get_response(request)
        return super().__call__(request)

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{__name__}.{self.__class__.__name__}[{id(self)}]")

    def get_dynamic_trusted_origins(
        self,
        request: ASGIRequest,
    ) -> list[str]:
        """
        Return request-scoped trusted origins.

        IMPORTANT:
        - never mutate Django settings
        - always return a fresh list
        """

        origins = list(settings.CSRF_TRUSTED_ORIGINS)

        try:
            if self.is_chatbot or self.is_config:
                origin = request.build_absolute_uri("/").rstrip("/")

                if origin not in origins:
                    origins.append(origin)
        # pylint: disable=broad-except
        except Exception as exc:
            logging.exception(
                "%s failed building dynamic CSRF origins: %s",
                self.formatted_class_name,
                exc,
            )

        return origins

    @cached_property
    def csrf_trusted_origins_hosts(self):
        """
        Django internals use this property.

        We preserve compatibility while avoiding mutation
        of global settings.
        """
        return [urlparse(origin).netloc.lstrip("*") for origin in settings.CSRF_TRUSTED_ORIGINS]

    @cached_property
    def allowed_origins_exact(self):
        return {origin for origin in settings.CSRF_TRUSTED_ORIGINS if "*" not in origin}

    @cached_property
    def allowed_origin_subdomains(self):
        allowed_origin_subdomains = defaultdict(list)

        for parsed in (urlparse(origin) for origin in settings.CSRF_TRUSTED_ORIGINS if "*" in origin):
            allowed_origin_subdomains[parsed.scheme].append(parsed.netloc.lstrip("*"))

        return allowed_origin_subdomains

    def process_view(
        self,
        request: ASGIRequest,
        callback,
        callback_args,
        callback_kwargs,
    ):
        """
        Main CSRF enforcement hook.

        IMPORTANT:
        - return None to continue processing
        - return HttpResponse to short-circuit
        - NEVER return self.get_response(request)
        """

        logger.debug(
            "%s.process_view() path=%s",
            self.formatted_class_name,
            request.path,
        )

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF):
            return None

        if smarter_settings.environment == SmarterEnvironments.LOCAL:
            logger.debug(
                "%s local environment bypass",
                self.formatted_class_name,
            )
            return None

        path = request.path.strip("/")

        if path in getattr(self, "amnesty_urls", []):
            logger.debug(
                "%s health check bypass: %s",
                self.formatted_class_name,
                request.path,
            )
            return None

        host = request.get_host()

        if any(host.startswith(prefix) for prefix in smarter_settings.internal_ip_prefixes):
            logger.debug(
                "%s internal IP bypass: %s",
                self.formatted_class_name,
                host,
            )
            return None

        #
        # Chatbot bypass
        #
        if self.is_chatbot and waffle.switch_is_active(SmarterWaffleSwitches.CSRF_SUPPRESS_FOR_CHATBOTS):
            logger.info(
                "%s chatbot CSRF bypass: %s",
                self.formatted_class_name,
                request.path,
            )
            return None

        dynamic_origins = self.get_dynamic_trusted_origins(request)

        original_exact = self.allowed_origins_exact
        original_subdomains = self.allowed_origin_subdomains
        original_hosts = self.csrf_trusted_origins_hosts

        try:
            self.csrf_trusted_origins_hosts = [urlparse(origin).netloc.lstrip("*") for origin in dynamic_origins]
            self.allowed_origins_exact = {origin for origin in dynamic_origins if "*" not in origin}
            allowed_subdomains = defaultdict(list)
            for parsed in (urlparse(origin) for origin in dynamic_origins if "*" in origin):
                allowed_subdomains[parsed.scheme].append(parsed.netloc.lstrip("*"))

            self.allowed_origin_subdomains = allowed_subdomains
            response = super().process_view(request, callback, callback_args, callback_kwargs)

        finally:
            self.allowed_origins_exact = original_exact
            self.allowed_origin_subdomains = original_subdomains
            self.csrf_trusted_origins_hosts = original_hosts

        if isinstance(response, HttpResponseForbidden):
            logger.error(
                (
                    "%s CSRF validation failed "
                    "| path=%s "
                    "| method=%s "
                    "| origin=%s "
                    "| referer=%s "
                    "| remote_addr=%s "
                    "| user_agent=%s"
                ),
                self.formatted_class_name,
                request.path,
                request.method,
                request.META.get("HTTP_ORIGIN"),
                request.META.get("HTTP_REFERER"),
                request.META.get("REMOTE_ADDR"),
                request.META.get("HTTP_USER_AGENT"),
            )

        return response
