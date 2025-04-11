"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

import fnmatch
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterWaffleSwitches
from smarter.lib.django import waffle

# from smarter.lib.django.http.shortcuts import SmarterHttpResponseBadRequest
from smarter.lib.django.validators import SmarterValidator

from ..models import ChatBot, get_cached_chatbot_by_request


logger = logging.getLogger(__name__)

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

    def process_request(self, request):

        # 1.) If the request is from a local host, allow it to pass through
        # ---------------------------------------------------------------------
        host = request.get_host()
        if host in SmarterValidator.LOCAL_HOSTS:
            if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                logger.info(
                    "%s %s found in SmarterValidator.LOCAL_HOSTS: %s",
                    self.formatted_class_name,
                    host,
                    SmarterValidator.LOCAL_HOSTS,
                )
            return None

        url = SmarterValidator.urlify(host, environment=smarter_settings.environment)
        parsed_host = urlparse(url)
        host = parsed_host.hostname

        # 2.) readiness and liveness checks
        # ---------------------------------------------------------------------
        path_parts = list(filter(None, parsed_host.path.split("/")))
        # if the entire path is healthz or readiness then we don't need to check
        if len(path_parts) == 1 and path_parts[0] in ["healthz", "readiness"]:
            if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
                logger.info(
                    "%s %s found in health/readiness check: %s",
                    self.formatted_class_name,
                    host,
                    path_parts,
                )
            return None

        # 3.) If the host is in the list of allowed hosts for
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

        # 4.) If the host is a domain for a deployed ChatBot, allow it to pass through
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

        if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
            logger.error("%s %s failed security tests.", self.formatted_class_name, url)
        return HttpResponseBadRequest(content="Bad Request (400) - Invalid Hostname.")
