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

        host = request.get_host()
        if not host.startswith(("http://", "https://")):
            host = "http://" + host

        parsed_host = urlparse(host)
        host = parsed_host.hostname
        if host in settings.SMARTER_ALLOWED_HOSTS:
            return None

        if ChatBot.get_by_url(host) is not None:
            return None

        return HttpResponseBadRequest("Bad Request (400) - Invalid Hostname.")
