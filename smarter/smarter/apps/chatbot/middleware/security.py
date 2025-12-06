"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

import fnmatch
import logging
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.middleware.security import SecurityMiddleware as DjangoSecurityMiddleware

from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..models import ChatBot, get_cached_chatbot_by_request


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING)
    ) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

logger.info("Loading smarter.apps.chatbot.middleware.security.SmarterSecurityMiddleware")


class SmarterSecurityMiddleware(DjangoSecurityMiddleware, SmarterHelperMixin):
    """
    This middleware overrides Django’s built-in ``SecurityMiddleware`` to provide custom host validation logic for the Smarter platform.

    **Key Features:**

    - **Custom Host Validation:**
      Instead of relying solely on Django’s ``ALLOWED_HOSTS``, this middleware introduces ``SMARTER_ALLOWED_HOSTS``. It checks incoming requests against both the traditional allowed hosts and a dynamic list of domains associated with deployed ChatBots.

    - **ChatBot Domain Support:**
      If the request’s host matches a domain for a deployed ChatBot, the request is allowed to pass through. This enables flexible multi-tenant deployments where each ChatBot can have its own domain.

    - **Friendly Error Handling:**
      The middleware suppresses Django’s default ``DisallowedHost`` exception. Instead, it returns a ``HttpResponseBadRequest`` (400) response, which is not logged and is more user-friendly for clients.

    - **Health Check Short-Circuiting:**
      Requests from internal IP addresses or for health/readiness endpoints are allowed to pass through without further validation. This ensures that infrastructure health checks do not get blocked by host validation.

    - **Logging:**
      Uses a custom logger that respects feature flags (waffle switches) for granular control over middleware and chatbot logging.

    **Request Validation Steps:**

    1. **Internal IPs:**
       Requests from internal IP addresses (e.g., load balancer health checks) are allowed.

    2. **Local Hosts:**
       Requests from local hosts (e.g., ``localhost``, ``127.0.0.1``) are allowed.

    3. **Health/Readiness URLs:**
       Requests to health or readiness endpoints are allowed.

    4. **Allowed Hosts:**
       Requests matching any pattern in ``SMARTER_ALLOWED_HOSTS`` are allowed.

    5. **ChatBot Domains:**
       Requests where the host matches a deployed ChatBot’s domain are allowed.

    6. **Fallback:**
       All other requests are rejected with a ``400 Bad Request`` response.

    **Example Usage:**

     .. code-block:: python

         MIDDLEWARE = [
             ...
             'smarter.apps.chatbot.middleware.security.SmarterSecurityMiddleware',
             ...
         ]

    """

    def process_request(self, request: WSGIRequest):

        logger.info(
            "%s.process_request() called for %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
        )

        # 1.) If the request is from an internal ip address, allow it to pass through
        # these typically originate from health checks from load balancers.
        # ---------------------------------------------------------------------
        # Short-circuit for health checks
        if request.path.replace("/", "") in self.amnesty_urls:
            return None

        host = request.get_host()
        if not host:
            return SmarterHttpResponseServerError(
                request=request,
                error_message="Internal error (500) - could not parse request.",
            )

        # Short-circuit for any requests born from internal IP address hosts
        # This is unlikely, but not impossible.
        if any(host.startswith(prefix) for prefix in settings.SMARTER_INTERNAL_IP_PREFIXES):
            logger.info(
                "%s %s identified as an internal IP address, exiting.",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request),
            )
            return None

        url = self.smarter_build_absolute_uri(request)

        # 2.) If the request is from a local host, allow it to pass through
        # ---------------------------------------------------------------------
        host_no_port = host.split(":")[0]
        base_host = host_no_port.split(".")[-1]
        if base_host in [h.rsplit(".", maxsplit=1)[-1] for h in SmarterValidator.LOCAL_HOSTS]:
            logger.info(
                "%s %s base host matched in SmarterValidator.LOCAL_HOSTS: %s",
                self.formatted_class_name,
                host,
                SmarterValidator.LOCAL_HOSTS,
            )
            return None

        if host in SmarterValidator.LOCAL_HOSTS:
            logger.info(
                "%s %s found in SmarterValidator.LOCAL_HOSTS: %s",
                self.formatted_class_name,
                host,
                SmarterValidator.LOCAL_HOSTS,
            )
            return None

        parsed_url = urlparse(url)

        # 3.) readiness and liveness checks
        # ---------------------------------------------------------------------
        path_parts = list(filter(None, parsed_url.path.split("/")))
        # if the entire path is healthz or readiness then we don't need to check
        if len(path_parts) == 1 and path_parts[0] in self.amnesty_urls:
            logger.info(
                "%s %s found in amnesty_urls: %s",
                self.formatted_class_name,
                host,
                path_parts,
            )
            return None

        # 4.) If the host is in the list of allowed hosts for
        #     our environment then allow it to pass through
        # ---------------------------------------------------------------------
        for allowed_host in settings.SMARTER_ALLOWED_HOSTS:
            if fnmatch.fnmatch(host, allowed_host):
                logger.info(
                    "%s %s matched with settings.SMARTER_ALLOWED_HOSTS: %s",
                    self.formatted_class_name,
                    host,
                    allowed_host,
                )
                return None

        # 5.) If the host is a domain for a deployed ChatBot, allow it to pass through
        #     FIX NOTE: this is ham fisted and should be refactored. we shouldn't need
        #     to instantiate a ChatBotHelper object just to check if the host is a domain
        #     for a deployed ChatBot.
        # ---------------------------------------------------------------------
        logger.info("%s instantiating ChatBotHelper() for url: %s", self.formatted_class_name, url)
        chatbot: Optional[ChatBot] = get_cached_chatbot_by_request(request=request)
        if chatbot is not None:
            logger.info("%s ChatBotHelper() verified that %s is a chatbot.", self.formatted_class_name, url)
            return None

        # 6.) Acme challenge requests should be allowed through
        #    http://platform.example.com/.well-known/acme-challenge/RYdbP7-MUXbQRZI1CZj-KKySBkHwHze8z04cjyN18Bk
        #    http://stackademy-sql.3141-5926-5359.api.example.com/.well-known/acme-challenge/QrRzO7QE7y6DhV8UqhfdD4_OoQ3Yh6XLR1qbJCRGcls
        # ---------------------------------------------------------------------
        if parsed_url.path.startswith("/.well-known/acme-challenge/"):
            logger.info(
                "%s %s identified as an ACME challenge request, exiting.",
                self.formatted_class_name,
                url,
            )
            return None

        # ---------------------------------------------------------------------
        # End of the road. Reject the request with a 400 Bad Request response.
        # ---------------------------------------------------------------------
        logger.error("%s %s failed security tests.", self.formatted_class_name, url)
        return SmarterHttpResponseBadRequest(
            request=request, error_message="SecurityMiddleware() Bad Request (400) - Invalid Hostname."
        )
