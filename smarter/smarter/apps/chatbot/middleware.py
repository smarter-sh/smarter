"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

from django.core.exceptions import SuspiciousOperation
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from .models import ChatBotApiUrlHelper


class SecurityMiddleware(DjangoSecurityMiddleware):
    """
    Override Django's SecurityMiddleware to suppress DisallowedHost exception
    for ChatBot API domains.
    """

    def process_request(self, request):
        try:
            super().process_request(request)
        except SuspiciousOperation:
            host = request.get_host()
            if ChatBotApiUrlHelper(url=host).is_valid:
                pass
            else:
                raise
