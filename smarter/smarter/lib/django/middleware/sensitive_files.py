"""
Middleware that blocks requests targeting sensitive files, configuration
artifacts, and common attack-probe endpoints.

This middleware detects suspicious path access attempts commonly associated
with automated scanners, vulnerability enumeration tools, credential
harvesting, and reconnaissance activity.

Key Features
============

- Blocks requests for sensitive files and directories
- Normalizes paths to reduce encoding bypasses
- Supports async and sync Django execution
- IP-based throttling for repeated suspicious requests
- Amnesty allowlist support
- Cached sensitive-path inspection
- Unicode normalization and traversal protection
- Feature-flag enablement via Django Waffle

Threat Mitigation
=================

This middleware helps mitigate several classes of reconnaissance and
probing attacks, including:

- exposed environment file discovery
- source-control directory probing
- credential and key harvesting attempts
- database backup discovery
- framework fingerprinting
- phpMyAdmin and admin-panel scanning
- path traversal and encoding bypass attempts
- automated vulnerability scanners

Behavior
========

For each request, the middleware:

#. Verifies middleware feature-flag enablement
#. Normalizes and decodes the request path
#. Applies amnesty allowlist checks
#. Resolves the client IP address
#. Applies IP-based throttling checks
#. Detects sensitive path patterns
#. Blocks suspicious requests with ``HTTP 403 Forbidden``

Repeated suspicious requests from the same client IP result in temporary
throttling.

Path Normalization
==================

Request paths undergo several normalization steps before inspection:

- repeated URL decoding
- Unicode normalization using ``NFKC``
- slash normalization
- null-byte removal
- duplicate slash collapsing
- traversal sequence normalization
- lowercase normalization

These transformations help mitigate common evasion techniques such as:

- double URL encoding
- mixed slash traversal
- Unicode homoglyph tricks
- null-byte injection

Sensitive Path Detection
========================

Sensitive resource detection supports:

- exact path matching
- glob-style wildcard matching
- segment-level inspection
- full-path inspection

Examples of protected resources include:

- ``.env``
- ``wp-config.php``
- ``settings.py``
- ``.git/``
- ``id_rsa``
- ``credentials.json``
- ``requirements.txt``
- ``composer.json``

Amnesty Support
================

Certain paths may bypass inspection through:

- configured amnesty URL lists
- regex-based allowlist patterns

Amnesty checks are applied before sensitive-file detection.

Caching
=======

Sensitive path inspection uses cached detection results to reduce
repeated pattern evaluation overhead.

Cached inspection results use a default timeout of 24 hours.

Throttle Configuration
======================

The middleware uses the following default limits:

- ``THROTTLE_LIMIT`` = 5 requests
- ``THROTTLE_TIMEOUT`` = 600 seconds

Throttle state is maintained per-client IP using the application cache
backend.

Cache keys use the format:

.. code-block:: text

   sensitive_files_throttle:<client_ip>

Async Compatibility
===================

The middleware supports both synchronous and asynchronous Django
execution models.

Coroutine-based request handlers are detected automatically during
middleware initialization.

Async request execution delegates synchronous request processing through
``sync_to_async()``.

Feature Flags
=============

Middleware activation is controlled using Django Waffle:

- ``ENABLE_MIDDLEWARE_SENSITIVE_FILES``

When disabled, the middleware behaves as a transparent pass-through.

Logging
=======

The middleware emits structured logs for:

- middleware initialization
- amnesty grants
- sensitive request blocking
- throttling events
- path normalization checks
- client IP resolution failures

Classes
=======

.. autosummary::
   :toctree: generated/

   SmarterBlockSensitiveFilesMiddleware

Dependencies
============

- Django
- asgiref
- Django Waffle
- application cache backend

Warnings
========

IP-based throttling may affect multiple users sharing the same public IP
address.

Care should be taken when deploying behind proxies or load balancers to
ensure correct client IP extraction.

Overly broad amnesty patterns may unintentionally weaken protection.

Notes
=====

This middleware depends on helper functionality provided by
:class:`smarter.common.mixins.SmarterMiddlewareMixin`.

Sensitive file inspection intentionally favors defensive matching and
may block requests resembling common attack patterns even if the target
resource does not exist.
"""

from __future__ import annotations

import fnmatch
import posixpath
import re
import unicodedata
import urllib.parse
from collections.abc import Awaitable, Callable, Iterable
from typing import cast

from asgiref.sync import sync_to_async
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    HttpResponseForbidden,
)

from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin, SmarterMiddlewareMixin
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

GetResponseCallable = Callable[[HttpRequest], HttpResponse]
AsyncGetResponseCallable = Callable[[HttpRequest], Awaitable[HttpResponse]]

logger = logging.getSmarterLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES):
    logger.debug(
        "%s is %s",
        formatted_text(__name__ + ".SmarterBlockSensitiveFilesMiddleware"),
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        formatted_text(__name__ + ".SmarterBlockSensitiveFilesMiddleware"),
        SmarterHelperMixin().formatted_state_not_ready,
    )


ALLOWED_PATTERNS = tuple(
    pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, re.IGNORECASE)
    for pattern in smarter_settings.sensitive_files_amnesty_patterns
)

SENSITIVE_FILES = frozenset(
    {
        ".env",
        "config.php",
        "wp-config.php",
        "settings.py",
        ".bak",
        "backup.sql",
        ".tmp",
        ".swp",
        ".git",
        ".svn",
        ".vscode",
        ".ds_store",
        "id_rsa",
        "id_dsa",
        "login.action",
        "info.php",
        "phpinfo.php",
        "php.ini",
        "phpmyadmin",
        "pma",
        "mysql",
        "db",
        "database",
        "backup",
        "dump",
        "sql",
        "sqlite",
        "mssql",
        "oracle",
        "postgres",
        "postgresql",
        "db.sqlite",
        "db.sqlite3",
        "db.mssql",
        "db.oracle",
        "db.postgres",
        "db.postgresql",
        "db.mysql",
        "db.sql",
        "composer.json",
        "composer.lock",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "gemfile",
        "gemfile.lock",
        "pipfile",
        "pipfile.lock",
        "requirements.txt",
        "credentials.json",
        "secrets.json",
        ".aws",
        ".ssh",
        ".npmrc",
        ".docker",
        "kubeconfig",
        "*.pem",
        "*.key",
        "*.crt",
        "*.cer",
        "*.p12",
        "*.pfx",
        "*.jks",
        "*.keystore",
        "*.env.local",
        "*.env.development",
        "*.env.production",
        "*.env.test",
        "*.env.qa",
        "*.env.staging",
        "*.env.*",
        "*.bak",
        "*.tmp",
        "*.swp",
        "*.log",
        "*.pid",
        "*.sock",
        "*.pid.lock",
        "*.pidfile",
        ".git/config",
        ".aws/credentials",
        ".docker/config.json",
        "ecp/current/exporttool/microsoft.exchange.ediscovery.exporttool.application",
    }
)

EXACT_MATCHES = frozenset(pattern for pattern in SENSITIVE_FILES if "*" not in pattern)
GLOB_MATCHES = frozenset(pattern for pattern in SENSITIVE_FILES if "*" in pattern)


class SmarterBlockSensitiveFilesMiddleware(SmarterMiddlewareMixin):
    """
    Middleware that blocks requests probing for sensitive files.

    Features:
    - ASGI and WSGI compatible
    - Path normalization
    - Amnesty support
    - Request throttling
    - Cached inspection
    """

    THROTTLE_LIMIT = 5
    THROTTLE_TIMEOUT = 600

    def __init__(self, get_response: GetResponseCallable | AsyncGetResponseCallable) -> None:
        super().__init__(get_response)

        self.allowed_patterns = ALLOWED_PATTERNS

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        if self.async_mode:
            return self.__acall__(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES):
            return self.get_response(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = self._inspect_request(request)

        if response is not None:
            return response

        return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponse:

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES):
            return await sync_to_async(self.get_response)(request)

        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = await sync_to_async(self._inspect_request)(request)

        if response is not None:
            return response

        get_response = cast(AsyncGetResponseCallable, self.get_response)
        return await get_response(request)

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{__name__}.{self.__class__.__name__}[{id(self)}]")

    def _inspect_request(
        self,
        request: HttpRequest,
    ) -> HttpResponse | None:

        normalized_path = self.normalize_path(request.path)

        if self.is_amnesty_path(normalized_path):
            logger.info(
                "%s amnesty granted to: %s",
                self.formatted_class_name,
                normalized_path,
            )
            return None

        client_ip = self.get_client_ip(request)

        if not client_ip:
            logger.warning(
                "%s could not determine client IP for request: %s",
                self.formatted_class_name,
                normalized_path,
            )
            return None

        if self.is_throttled(client_ip):
            logger.warning(
                "%s throttled client: %s",
                self.formatted_class_name,
                client_ip,
            )

            return HttpResponseForbidden(
                "Too many suspicious requests detected. " f"Contact {SMARTER_CUSTOMER_SUPPORT_EMAIL} for assistance."
            )

        if self.is_sensitive_request(normalized_path):

            logger.warning(
                "%s blocked sensitive request: %s",
                self.formatted_class_name,
                normalized_path,
            )

            self.increment_throttle(client_ip)

            return HttpResponseForbidden(
                "Your request has been blocked by Smarter. " f"Contact {SMARTER_CUSTOMER_SUPPORT_EMAIL} for assistance."
            )

        return None

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize paths to reduce traversal and encoding bypasses.
        """

        for _ in range(2):
            path = urllib.parse.unquote(path)

        path = unicodedata.normalize("NFKC", path)

        path = path.replace("\\", "/")
        path = path.replace("\x00", "")

        path = re.sub(r"/+", "/", path)

        path = posixpath.normpath(path)

        if not path.startswith("/"):
            path = f"/{path}"

        return path.lower()

    def is_amnesty_path(self, path: str) -> bool:

        if path.replace("/", "") in self.amnesty_urls:
            return True

        for pattern in self.allowed_patterns:
            if pattern.match(path):
                return True

        for segment in self.iter_path_segments(path):
            for pattern in self.allowed_patterns:
                if pattern.match(segment):
                    return True

        return False

    def is_throttled(self, client_ip: str) -> bool:

        throttle_key = self.get_throttle_key(client_ip)

        blocked_count = cache.get(throttle_key, 0)

        return blocked_count >= self.THROTTLE_LIMIT

    def increment_throttle(self, client_ip: str) -> None:

        throttle_key = self.get_throttle_key(client_ip)

        try:
            blocked_count = cache.incr(throttle_key)

        except ValueError:
            cache.set(
                throttle_key,
                1,
                timeout=self.THROTTLE_TIMEOUT,
            )

        else:
            cache.set(
                throttle_key,
                blocked_count,
                timeout=self.THROTTLE_TIMEOUT,
            )

    @staticmethod
    def get_throttle_key(client_ip: str) -> str:
        return f"sensitive_files_throttle:{client_ip}"

    @staticmethod
    def iter_path_segments(path: str) -> Iterable[str]:
        return (segment for segment in path.split("/") if segment)

    @classmethod
    @cache_results(timeout=60 * 60 * 24)
    def is_sensitive_request(cls, path: str) -> bool:
        """
        Cached sensitive file detection.
        """

        path_segments = tuple(cls.iter_path_segments(path))

        logger.debug(
            "%s checking normalized path: %s",
            cls.__name__,
            path,
        )

        normalized_full_path = path.lstrip("/")

        if normalized_full_path in EXACT_MATCHES:
            return True

        for pattern in GLOB_MATCHES:
            if fnmatch.fnmatch(normalized_full_path, pattern):
                return True

        for segment in path_segments:
            if segment in EXACT_MATCHES:
                return True

        for segment in path_segments:
            for pattern in GLOB_MATCHES:
                if fnmatch.fnmatch(segment, pattern):
                    return True

        return False
