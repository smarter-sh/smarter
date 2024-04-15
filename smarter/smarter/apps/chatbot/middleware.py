"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from .models import ChatBot


class SecurityMiddleware(DjangoSecurityMiddleware):
    """
    Override Django's SecurityMiddleware to suppress DisallowedHost exception
    for ChatBot API domains.
    """

    def process_request(self, request):

        host = request.get_host()
        if host in settings.ALLOWED_HOSTS:
            return None

        if ChatBot.get_by_url(host) is not None:
            return None

        raise DisallowedHost
