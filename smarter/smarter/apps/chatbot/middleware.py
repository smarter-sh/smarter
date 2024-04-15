"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

from django.core.exceptions import SuspiciousOperation
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from .models import ChatBot


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
            # Check if the host is a ChatBot API domain.
            # If it is, then suppress the SuspiciousOperation exception.
            # This is a cached operation, so it should not affect performance.
            if ChatBot.get_by_url(host) is not None:
                pass
            else:
                raise
