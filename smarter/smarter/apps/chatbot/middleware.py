"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

import logging
import string
from collections import defaultdict
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.middleware.csrf import CsrfViewMiddleware as DjangoCsrfViewMiddleware
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property

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


###############################################################################
# CSRF Middleware
###############################################################################
CSRF_SECRET_LENGTH = 32
CSRF_ALLOWED_CHARS = string.ascii_letters + string.digits


def _get_new_csrf_string():
    return get_random_string(CSRF_SECRET_LENGTH, allowed_chars=CSRF_ALLOWED_CHARS)


def _add_new_csrf_cookie(request):
    """Generate a new random CSRF_COOKIE value, and add it to request.META."""
    csrf_secret = _get_new_csrf_string()
    request.META.update(
        {
            "CSRF_COOKIE": csrf_secret,
            "CSRF_COOKIE_NEEDS_UPDATE": True,
        }
    )
    return csrf_secret


class InvalidTokenFormat(Exception):
    """The token has an invalid format."""

    def __init__(self, reason):
        self.reason = reason


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

        try:
            csrf_secret = self._get_secret(request)
        except InvalidTokenFormat:
            _add_new_csrf_cookie(request)
        else:
            if csrf_secret is not None:
                # Use the same secret next time. If the secret was originally
                # masked, this also causes it to be replaced with the unmasked
                # form, but only in cases where the secret is already getting
                # saved anyways.
                request.META["CSRF_COOKIE"] = csrf_secret
