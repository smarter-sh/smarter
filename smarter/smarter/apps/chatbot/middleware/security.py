"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

import logging
from urllib.parse import urlparse

import waffle
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterWaffleSwitches
from smarter.lib.django.validators import SmarterValidator

from ..models import ChatBotHelper


logger = logging.getLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
    logger.info("Loading smarter.apps.chatbot.middleware.security.SecurityMiddleware")


class SecurityMiddleware(DjangoSecurityMiddleware):
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
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info(
                    "SecurityMiddleware() %s found in SmarterValidator.LOCAL_HOSTS: %s",
                    host,
                    SmarterValidator.LOCAL_HOSTS,
                )
            return None

        url = SmarterValidator.urlify(host, environment=smarter_settings.environment)
        parsed_host = urlparse(url)
        host = parsed_host.hostname

        # 2.) If the host is in the list of allowed hosts for
        #     our environment then allow it to pass through
        # ---------------------------------------------------------------------
        if host in settings.SMARTER_ALLOWED_HOSTS:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info(
                    "SecurityMiddleware() %s found in settings.SMARTER_ALLOWED_HOSTS: %s",
                    host,
                    settings.SMARTER_ALLOWED_HOSTS,
                )
            return None

        # 3.) If the host is a domain for a deployed ChatBot, allow it to pass through
        #     FIX NOTE: this is ham fisted and should be refactored. we shouldn't need
        #     to instantiate a ChatBotHelper object just to check if the host is a domain
        #     for a deployed ChatBot.
        # ---------------------------------------------------------------------
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
            logger.info("SecurityMiddleware() instantiating ChatBotHelper() for url: %s", url)
        helper = ChatBotHelper(url=url, user=request.user)
        if helper.chatbot is not None:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info("SecurityMiddleware() ChatBotHelper() verified that %s is a chatbot.", url)
            return None

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
            logger.error("SecurityMiddleware() %s failed security tests.", url)
        return HttpResponseBadRequest("Bad Request (400) - Invalid Hostname.")
