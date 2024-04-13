"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseBadRequest

from .models import ChatBotCustomDomain


class AllowCustomDomainsMiddleware:
    """Suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Handle custom domain names."""
        host = request.get_host()
        if host in ChatBotCustomDomain.get_verified_domains() and host not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append(host)

        try:
            response = self.get_response(request)
        except DisallowedHost:
            # Return a 400 Bad Request response instead of raising DisallowedHost
            return HttpResponseBadRequest()

        return response
