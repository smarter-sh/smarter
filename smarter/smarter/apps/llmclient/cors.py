"""
Per-LLMClient CORS origins.

A web page that embeds Smarter Chat (the ``@smarter.sh/ui-chat`` npm package) calls its LLMClient's
configuration and prompt apis from the browser, cross-origin, with credentials. The platform's CORS
settings (``CORS_ALLOWED_ORIGINS`` and ``CORS_ALLOWED_ORIGIN_REGEXES``) allow the platform's own
origins. An LLMClient's manifest can allow more, in ``spec.config.allowedOrigins``, which this module
applies, through ``django-cors-headers``' ``check_request_enabled`` signal: a receiver that returns
True allows the request's origin, for preflight requests and for the requests themselves.

Only the apis that Smarter Chat calls are considered:

- a deployed LLMClient's own host (or custom domain): ``/``, ``/config/`` and ``/prompt/``,
- the platform api: ``/api/v1/llm-clients/<hashed_id or id>/config/``, ``.../prompt/`` and
  ``.../prompt/config/``.
"""

import re
from typing import Optional

from corsheaders.signals import check_request_enabled
from django.dispatch import receiver
from django.http import HttpRequest

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import LLMClient, get_cached_llmclient_by_request
from .models.utils import LLMCLIENT_HOST_PATHS

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING, SmarterWaffleSwitches.MIDDLEWARE_LOGGING]
)

API_PATH_PATTERN = re.compile(r"^/api/v1/llm-clients/(?P<identifier>[\w-]+)/(?:config/|prompt/|prompt/config/)$")
"""The platform api paths of an LLMClient's configuration and prompt apis."""


def _host(request: HttpRequest) -> str:
    """The request's host, without its port."""
    try:
        return request.get_host().split(":")[0].lower()
    # pylint: disable=broad-exception-caught
    except Exception:
        return ""


def _platform_hosts() -> set[str]:
    """The hosts of the platform itself, which are never a deployed LLMClient's."""
    return {
        str(host).split(":")[0].lower()
        for host in (smarter_settings.environment_platform_domain, smarter_settings.environment_api_domain)
        if host
    }


def llmclient_for_cors(request: HttpRequest) -> Optional[LLMClient]:
    """
    The LLMClient whose configuration or prompt api the request calls, if any.

    :param request: The request, which may be a CORS preflight request.
    :type request: django.http.HttpRequest
    :returns: The LLMClient, or None if the request isn't for one of its apis.
    :rtype: Optional[LLMClient]
    """
    match = API_PATH_PATTERN.match(request.path)
    if match:
        identifier = match.group("identifier")
        try:
            llmclient_id = int(identifier) if identifier.isdigit() else LLMClient.id_from_hashed_id(identifier)
            return LLMClient.get_cached_object(pk=llmclient_id)
        # pylint: disable=broad-exception-caught
        except Exception:
            return None
    if request.path in LLMCLIENT_HOST_PATHS and _host(request) not in _platform_hosts():
        try:
            return get_cached_llmclient_by_request(request)
        # pylint: disable=broad-exception-caught
        except Exception:
            return None
    return None


def origin_allowed(origin: Optional[str], llmclient: Optional[LLMClient]) -> bool:
    """
    Whether the LLMClient allows the origin.

    :param origin: The request's ``Origin`` header.
    :type origin: Optional[str]
    :param llmclient: The LLMClient.
    :type llmclient: Optional[LLMClient]
    :returns: True if the origin is in the LLMClient's ``allowed_origins``.
    :rtype: bool
    """
    if not origin or not llmclient:
        return False
    allowed = llmclient.allowed_origins or []
    return origin.strip().lower().rstrip("/") in allowed


@receiver(check_request_enabled, dispatch_uid="smarter.apps.llmclient.cors.allow_llmclient_origins")
def allow_llmclient_origins(sender, request: HttpRequest, **kwargs) -> bool:
    """
    Allow a cross-origin request whose origin its LLMClient's manifest allows.

    Called by ``django-cors-headers`` for each request whose origin the platform's CORS settings don't
    allow. It never raises: a request that can't be resolved is simply not allowed here.

    :param sender: None.
    :param request: The request.
    :type request: django.http.HttpRequest
    :returns: True to allow the request's origin.
    :rtype: bool
    """
    origin = request.headers.get("Origin")
    if not origin:
        return False
    llmclient = llmclient_for_cors(request)
    allowed = origin_allowed(origin, llmclient)
    if allowed:
        logger.debug("%s allowed origin %s for llmclient %s", __name__, origin, llmclient)
    return allowed


__all__ = ["allow_llmclient_origins", "llmclient_for_cors", "origin_allowed"]
