"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

import logging
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from smarter.lib.django.validators import SmarterValidator

from .models import ChatBot


logger = logging.getLogger(__name__)


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
        host = request.get_host()
        if host in SmarterValidator.LOCAL_HOSTS:
            return None

        url = SmarterValidator.urlify(host)
        parsed_host = urlparse(url)
        host = parsed_host.hostname

        # 2.) If the host is in the list of allowed hosts for
        #     our environment then allow it to pass through
        if host in settings.SMARTER_ALLOWED_HOSTS:
            return None

        # 3.) If the host is a domain for a deployed ChatBot, allow it to pass through
        if ChatBot.get_by_url(url) is not None:
            return None

        return HttpResponseBadRequest("Bad Request (400) - Invalid Hostname.")
