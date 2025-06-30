"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

import fnmatch
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from smarter.common.classes import SmarterHelperMixin
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..models import ChatBot, get_cached_chatbot_by_request


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING)
    ) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
    logger.info("Loading smarter.apps.chatbot.middleware.security.SecurityMiddleware")


class SecurityMiddleware(DjangoSecurityMiddleware, SmarterHelperMixin):
    """
    Override Django's SecurityMiddleware to create our own implementation
    of ALLOWED_HOSTS, referred to as SMARTER_ALLOWED_HOSTS.

    We not only need to evaluate the traditional list of ALLOWED_HOSTS, but
    also need to check if the host is a domain for a deployed ChatBot. If the
    host is a domain for a deployed ChatBot, we should allow the request to
    pass through.

    This middleware is also used to suppress the stock DisallowedHost exception
    in favor of our own HttpResponseBadRequest response, which is a non-logged
    response that is more user-friendly.

    """

    def process_request(self, request: WSGIRequest):

        # 1.) If the request is from an internal ip address, allow it to pass through
        # these typically originate from health checks from load balancers.
        # ---------------------------------------------------------------------
        host = request.get_host()
        if not host:
            return SmarterHttpResponseServerError(
                request=request,
                error_message="Internal error (500) - could not parse request.",
            )

        internal_ip_prefixes = ["192.168."]
        if any(host.startswith(prefix) for prefix in internal_ip_prefixes):
            if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                logger.info(
                    "%s %s identified as an internal IP address, allowing request.",
                    self.formatted_class_name,
                    host,
                )
            return None

        # 2.) If the request is from a local host, allow it to pass through
        # ---------------------------------------------------------------------
        host_no_port = host.split(":")[0]
        base_host = host_no_port.split(".")[-1]
        if base_host in [h.rsplit(".", maxsplit=1)[-1] for h in SmarterValidator.LOCAL_HOSTS]:
            if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                logger.info(
                    "%s %s base host matched in SmarterValidator.LOCAL_HOSTS: %s",
                    self.formatted_class_name,
                    host,
                    SmarterValidator.LOCAL_HOSTS,
                )
            return None

        if host in SmarterValidator.LOCAL_HOSTS:
            if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                logger.info(
                    "%s %s found in SmarterValidator.LOCAL_HOSTS: %s",
                    self.formatted_class_name,
                    host,
                    SmarterValidator.LOCAL_HOSTS,
                )
            return None

        url = self.smarter_build_absolute_uri(request)
        parsed_url = urlparse(url)

        # 3.) readiness and liveness checks
        # ---------------------------------------------------------------------
        path_parts = list(filter(None, parsed_url.path.split("/")))
        # if the entire path is healthz or readiness then we don't need to check
        if len(path_parts) == 1 and path_parts[0] in self.amnesty_urls:
            if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                logger.info(
                    "%s %s found in amnesty_urls: %s",
                    self.formatted_class_name,
                    host,
                    path_parts,
                )
            return None

        # 4.) If the host is in the list of allowed hosts for
        #     our environment then allow it to pass through
        # ---------------------------------------------------------------------
        for allowed_host in settings.SMARTER_ALLOWED_HOSTS:
            if fnmatch.fnmatch(host, allowed_host):
                if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                    logger.info(
                        "%s %s matched with settings.SMARTER_ALLOWED_HOSTS: %s",
                        self.formatted_class_name,
                        host,
                        allowed_host,
                    )
                return None

        # 5.) If the host is a domain for a deployed ChatBot, allow it to pass through
        #     FIX NOTE: this is ham fisted and should be refactored. we shouldn't need
        #     to instantiate a ChatBotHelper object just to check if the host is a domain
        #     for a deployed ChatBot.
        # ---------------------------------------------------------------------
        if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
            logger.info("%s instantiating ChatBotHelper() for url: %s", self.formatted_class_name, url)
        chatbot: ChatBot = get_cached_chatbot_by_request(request=request)
        if chatbot is not None:
            if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                logger.info("%s ChatBotHelper() verified that %s is a chatbot.", self.formatted_class_name, url)
            return None

        logger.error("%s %s failed security tests.", self.formatted_class_name, url)
        return SmarterHttpResponseBadRequest(
            request=request, error_message="SecurityMiddleware() Bad Request (400) - Invalid Hostname."
        )
