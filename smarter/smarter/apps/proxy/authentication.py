"""
Authentication of the Proxy passthrough's callers, with a Smarter API key.

A Proxy's callers use the provider's own SDK, with the Proxy's URL as its base URL, and a
Smarter API key in place of the provider's. Each SDK sends its API key in its own header, so
:class:`SmarterProxyAuthentication` reads the Smarter API key from any of them. See
:data:`~smarter.apps.proxy.const.CREDENTIAL_HEADERS`.

.. code-block:: python

    from openai import OpenAI

    client = OpenAI(
        base_url="https://platform.smarter.sh/api/v1/proxy/openai/",
        api_key="<your Smarter API key>",
    )
"""

from typing import Optional

from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])

AUTHORIZATION_SCHEMES = ("bearer", "token")
API_KEY_HEADERS = ("HTTP_X_API_KEY", "HTTP_X_GOOG_API_KEY", "HTTP_API_KEY")
"""The request.META keys of the x-api-key (Anthropic), x-goog-api-key (Google Gemini) and api-key (Azure OpenAI) headers."""


def get_api_key(request: Request) -> Optional[str]:
    """
    The Smarter API key of a request: from ``Authorization: Bearer <key>`` or ``Authorization: Token <key>``,.

    else from the ``x-api-key``, ``x-goog-api-key`` or ``api-key`` header.

    :returns: The API key, or ``None`` if there is none.
    :raises AuthenticationFailed: if the Authorization header is malformed.
    """
    authorization = request.META.get("HTTP_AUTHORIZATION", "").strip()
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() not in AUTHORIZATION_SCHEMES:
            raise AuthenticationFailed("Invalid Authorization header. Use 'Authorization: Bearer <Smarter API key>'.")
        return parts[1]
    for header in API_KEY_HEADERS:
        value = request.META.get(header, "").strip()
        if value:
            return value
    return None


class SmarterProxyAuthentication(BaseAuthentication):
    """
    Authenticate a Proxy's caller by a Smarter API key, in any of the headers that LLM SDKs use.

    The key is verified by :class:`~smarter.lib.drf.token_authentication.SmarterTokenAuthentication`,
    as for the rest of the Smarter API: it must exist, and be active.
    """

    def authenticate(self, request: Request) -> Optional[tuple[User, SmarterAuthToken]]:
        api_key = get_api_key(request)
        if not api_key:
            return None
        return SmarterTokenAuthentication().authenticate_credentials(api_key.encode("utf-8"))

    def authenticate_header(self, request: Request) -> str:
        """The WWW-Authenticate header of a 401 response, so that DRF returns 401 rather than 403."""
        return 'Bearer realm="smarter-proxy"'


__all__ = ["SmarterProxyAuthentication", "get_api_key"]
