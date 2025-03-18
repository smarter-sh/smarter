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

from smarter.apps.chatbot.models import ChatBot, get_cached_chatbot_by_request
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterWaffleSwitches


logger = logging.getLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
    logger.info("Loading smarter.apps.chatbot.middleware.csrf.CsrfViewMiddleware")


class CsrfViewMiddleware(DjangoCsrfViewMiddleware, SmarterHelperMixin):
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
        # Does this url point to a ChatBot?
        # ------------------------------------------------------
        try:
            self.chatbot = get_cached_chatbot_by_request(request=request)
        # pylint: disable=broad-except
        except Exception:
            # this is not a ChatBot request
            self.chatbot = None

        if self.chatbot and waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
            logger.info("%s.process_request: csrf_middleware_logging is active", self.formatted_class_name)
            logger.info("=" * 80)
            logger.info("%s ChatBot: %s", self.formatted_class_name, self.chatbot)
            for cookie in request.COOKIES:
                logger.info("CsrfViewMiddleware request.COOKIES: %s", cookie)
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

        if self.chatbot:
            logger.info("%s ChatBot: %s is csrf exempt.", self.formatted_class_name, self.chatbot)
            return None

        # ------------------------------------------------------
        return super().process_request(request)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if smarter_settings.environment == "local":
            logger.debug("%s._accept: environment is local. ignoring csrf checks", self.formatted_class_name)
            return None
        if self.chatbot and waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_SUPPRESS_FOR_CHATBOTS):
            logger.info(
                "%s.process_view: %s is active",
                self.formatted_class_name,
                SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_SUPPRESS_FOR_CHATBOTS,
            )
            response = super().process_view(request, callback, callback_args, callback_kwargs)
            if isinstance(response, HttpResponseForbidden):
                logger.error("%s CSRF validation failed", self.formatted_class_name)
                return None
            return response
        return super().process_view(request, callback, callback_args, callback_kwargs)
