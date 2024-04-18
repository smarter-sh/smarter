"""
This module contains the CsrfViewMiddleware class, which is a subclass of Django's
CsrfViewMiddleware. It adds the ability to add the ChatBot's URL to the list of
trusted origins for CSRF protection.
"""

import logging
from collections import defaultdict
from urllib.parse import urlparse

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware as DjangoCsrfViewMiddleware
from django.utils.functional import cached_property

from smarter.lib.django.validators import SmarterValidator

from ..models import ChatBot


logger = logging.getLogger(__name__)


class CsrfViewMiddleware(DjangoCsrfViewMiddleware):
    """
    Require a present and correct csrfmiddlewaretoken for POST requests that
    have a CSRF cookie, and set an outgoing CSRF cookie.

    This middleware should be used in conjunction with the {% csrf_token %}
    template tag.
    """

    chatbot: ChatBot = None

    @cached_property
    def CSRF_TRUSTED_ORIGINS(self) -> list[str]:
        """
        Return the list of trusted origins for CSRF.
        If the request is for a ChatBot, the ChatBot's URL is added to the list.
        """
        retval = settings.CSRF_TRUSTED_ORIGINS
        if self.chatbot is not None:
            retval += [self.chatbot.url]
        return retval

    @cached_property
    def csrf_trusted_origins_hosts(self):
        return [urlparse(origin).netloc.lstrip("*") for origin in self.CSRF_TRUSTED_ORIGINS]

    @cached_property
    def allowed_origins_exact(self):
        return {origin for origin in self.CSRF_TRUSTED_ORIGINS if "*" not in origin}

    @cached_property
    def allowed_origin_subdomains(self):
        """
        A mapping of allowed schemes to list of allowed netlocs, where all
        subdomains of the netloc are allowed.
        """
        allowed_origin_subdomains = defaultdict(list)
        for parsed in (urlparse(origin) for origin in self.CSRF_TRUSTED_ORIGINS if "*" in origin):
            allowed_origin_subdomains[parsed.scheme].append(parsed.netloc.lstrip("*"))
        return allowed_origin_subdomains

    def process_request(self, request):

        # Attempt to initialize a ChatBot instance based on the request's host.
        # ------------------------------------------------------
        host = request.get_host()
        url = SmarterValidator.urlify(host)
        parsed_host = urlparse(url)
        host = parsed_host.hostname
        self.chatbot = ChatBot.get_by_url(url)
        # ------------------------------------------------------
        super().process_request(request)
