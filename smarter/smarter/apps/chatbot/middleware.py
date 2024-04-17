"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from .models import ChatBot


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
        LOCAL_HOSTS = ["localhost", "127.0.0.1", "testserver"]
        host = request.get_host()
        if host in LOCAL_HOSTS:
            return None

        if not host.startswith(("http://", "https://")):
            host = "http://" + host
        parsed_host = urlparse(host)
        host = parsed_host.hostname

        # 2.) If the host is in the list of allowed hosts for
        #     our environment then allow it to pass through
        if host in settings.SMARTER_ALLOWED_HOSTS:
            return None

        # 3.) If the host is a domain for a deployed ChatBot, allow it to pass through
        if ChatBot.get_by_url(host) is not None:
            return None

        return HttpResponseBadRequest("Bad Request (400) - Invalid Hostname.")
