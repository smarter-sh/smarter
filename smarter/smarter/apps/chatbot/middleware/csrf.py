"""
This module contains the CsrfViewMiddleware class, which is a subclass of Django's
CsrfViewMiddleware. It adds the ability to add the ChatBot's URL to the list of
trusted origins for CSRF protection.
"""

import logging
from collections import defaultdict
from urllib.parse import urlparse

import waffle
from django.conf import settings
from django.http import HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware as DjangoCsrfViewMiddleware
from django.utils.functional import cached_property

from smarter.apps.chatbot.models import ChatBot
from smarter.common.conf import settings as smarter_settings


logger = logging.getLogger(__name__)


class CsrfViewMiddleware(DjangoCsrfViewMiddleware):
    """
    Require a present and correct csrfmiddlewaretoken for POST requests that
    have a CSRF cookie, and set an outgoing CSRF cookie.

    This middleware should be used in conjunction with the {% csrf_token %}
    template tag.
    """

    chatbot: ChatBot = None

    @cached_property
    def CSRF_TRUSTED_ORIGINS(self) -> list[str]:
        """
        Return the list of trusted origins for CSRF.
        If the request is for a ChatBot, the ChatBot's URL is added to the list.
        """
        retval = settings.CSRF_TRUSTED_ORIGINS
        if self.chatbot is not None:
            retval += [self.chatbot.url]
        logger.info("CsrfViewMiddleware.CSRF_TRUSTED_ORIGINS: %s", retval)
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
        # Does this url point to a ChatBot?
        # ------------------------------------------------------
        self.chatbot = ChatBot.get_by_request(request=request)
        if self.chatbot and waffle.switch_is_active("csrf_middleware_logging"):
            logger.info("CsrfViewMiddleware.process_request: csrf_middleware_logging is active")
            logger.info("=" * 80)
            logger.info("CsrfViewMiddleware ChatBot: %s", self.chatbot)
            for cookie in request.COOKIES:
                logger.info("CsrfViewMiddleware request.COOKIES: %s", cookie)
            logger.info("CsrfViewMiddleware cookie settings")
            logger.info("CsrfViewMiddleware settings.CSRF_COOKIE_NAME: %s", settings.CSRF_COOKIE_NAME)
            logger.info("CsrfViewMiddleware request.META['CSRF_COOKIE']: %s", request.META.get("CSRF_COOKIE"))
            logger.info("CsrfViewMiddleware settings.CSRF_COOKIE_AGE: %s", settings.CSRF_COOKIE_AGE)
            logger.info("CsrfViewMiddleware settings.CSRF_COOKIE_DOMAIN: %s", settings.CSRF_COOKIE_DOMAIN)
            logger.info("CsrfViewMiddleware settings.CSRF_COOKIE_PATH: %s", settings.CSRF_COOKIE_PATH)
            logger.info("CsrfViewMiddleware settings.CSRF_COOKIE_SECURE: %s", settings.CSRF_COOKIE_SECURE)
            logger.info("CsrfViewMiddleware settings.CSRF_COOKIE_HTTPONLY: %s", settings.CSRF_COOKIE_HTTPONLY)
            logger.info("CsrfViewMiddleware settings.CSRF_COOKIE_SAMESITE: %s", settings.CSRF_COOKIE_SAMESITE)
            logger.info("=" * 80)

        # ------------------------------------------------------
        super().process_request(request)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if smarter_settings.environment == "local":
            logger.debug("CsrfViewMiddleware._accept: environment is local. ignoring csrf checks")
            return None
        if self.chatbot and waffle.switch_is_active("csrf_middleware_suppress_for_chatbots"):
            logger.info("CsrfViewMiddleware.process_view: csrf_middleware_suppress_for_chatbots is active")
            response = super().process_view(request, callback, callback_args, callback_kwargs)
            if isinstance(response, HttpResponseForbidden):
                logger.error("CSRF validation failed")
                return None
            return response
        return super().process_view(request, callback, callback_args, callback_kwargs)
