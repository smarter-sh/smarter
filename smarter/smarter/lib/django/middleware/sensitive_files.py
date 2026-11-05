"""
Middleware that blocks requests targeting sensitive files, configuration artifacts, and common attack-probe endpoints.

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
- In-memory sensitive-path inspection, with one precompiled pattern
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
#. Answers a sensitive path with the platform's ordinary ``404 Not Found``

A blocked path gets exactly the response of any url that does not exist, so a
scanner cannot tell that it was blocked, nor that the path is of interest.

Repeated suspicious requests from the same client IP result in temporary
throttling: ``429 Too Many Requests``, with a ``Retry-After`` header of
``THROTTLE_TIMEOUT`` seconds.

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

The glob patterns are compiled once, into one regular expression, and each
process remembers the result for the most recent paths in memory. Nothing is
cached in Redis: the check costs microseconds, which is less than a round trip,
and a changed pattern list applies as soon as a process starts.

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

The logs name the request's path, never the client's IP address, which is
personal data.

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
from functools import cached_property, lru_cache
from typing import cast

from asgiref.sync import sync_to_async
from cache_results import lazy_cache as cache
from django.core.handlers.exception import response_for_exception
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
)

from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.mixins import SmarterHelperMixin, SmarterMiddlewareMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

GetResponseCallable = Callable[[HttpRequest], HttpResponse]
AsyncGetResponseCallable = Callable[[HttpRequest], Awaitable[HttpResponse]]

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES):
    logger.debug(
        "%s is %s",
        SmarterFormattedText.text(__name__) + ".SmarterBlockSensitiveFilesMiddleware",
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        SmarterFormattedText.text(__name__) + ".SmarterBlockSensitiveFilesMiddleware",
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

GLOB_REGEX = re.compile("|".join(fnmatch.translate(pattern) for pattern in sorted(GLOB_MATCHES)))
"""Every pattern of :data:`GLOB_MATCHES`, compiled once into one regular expression."""

SENSITIVE_PATH_CACHE_SIZE = 4096
"""How many recent paths each process remembers the result of :func:`is_sensitive_path` for."""

REPEATED_SLASHES = re.compile(r"/+")
"""Collapses repeated slashes in a request path."""


class SmarterBlockSensitiveFilesMiddleware(SmarterMiddlewareMixin):
    """
    Middleware that blocks requests probing for sensitive files.

    **Features:**

    - ASGI and WSGI compatible
    - Path normalization
    - Amnesty support
    - Request throttling
    - In-memory inspection
    """

    THROTTLE_LIMIT = 5
    THROTTLE_TIMEOUT = 600

    def __init__(self, get_response: GetResponseCallable | AsyncGetResponseCallable) -> None:
        super().__init__(get_response)

        self.allowed_patterns = ALLOWED_PATTERNS

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        """
        Inspect a request synchronously, or hand it to :meth:`__acall__` in async mode.

        An amnesty path, or a request while ``ENABLE_MIDDLEWARE_SENSITIVE_FILES`` is off, passes
        through untouched.

        :param request: The incoming request.
        :returns: A ``429`` if the client is throttled, the platform's ``404`` for a sensitive
            path, or otherwise the next handler's response (a coroutine in async mode).
        """
        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return super().__call__(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES):
            return super().__call__(request)

        response = self._inspect_request(request)

        if response is not None:
            return response

        return super().__call__(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        """
        Inspect a request in async mode, running the synchronous inspection in a thread.

        :param request: The incoming request.
        :returns: A ``429`` if the client is throttled, the platform's ``404`` for a sensitive
            path, or otherwise the next handler's response.
        """
        if self.deserves_amnesty(request.path):
            return await super().__acall__(request)

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES):
            return await super().__acall__(request)

        response = await sync_to_async(self._inspect_request)(request)

        if response is not None:
            return response

        get_response = cast(AsyncGetResponseCallable, self.get_response)
        return await get_response(request)

    @cached_property
    def formatted_class_name(self) -> str:
        """Return the formatted class name for logging.

        It names the instance, not a request.
        """
        class_name = f"{__name__}.{self.__class__.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def _inspect_request(
        self,
        request: HttpRequest,
    ) -> HttpResponse | None:
        """
        Check a request's path and client against the amnesty list, the throttle and the sensitive files.

        Side effect: a sensitive path adds one to the client's probe count in the cache.

        :param request: The incoming request.
        :returns: A ``429`` if the client is throttled, the platform's ``404`` for a sensitive
            path, or None to let the request through.
        """
        normalized_path = self.normalize_path(request.path)

        if self.is_amnesty_path(normalized_path):
            return None

        client_ip = self.get_client_ip(request)

        if not client_ip:
            logger.warning(
                "%s._inspect_request() could not determine client IP for request: %s",
                self.formatted_class_name,
                normalized_path,
            )
            return None

        if self.is_throttled(client_ip):
            # the client's IP address is personal data: log the path, never the address.
            logger.warning(
                "%s._inspect_request() throttled request: %s",
                self.formatted_class_name,
                normalized_path,
            )

            throttled = HttpResponse(
                "Too many suspicious requests detected. " f"Contact {SMARTER_CUSTOMER_SUPPORT_EMAIL} for assistance.",
                status=429,
                content_type="text/plain",
            )
            throttled["Retry-After"] = str(self.THROTTLE_TIMEOUT)
            return throttled

        if self.is_sensitive_request(normalized_path):

            logger.warning(
                "%s._inspect_request() blocked sensitive request: %s",
                self.formatted_class_name,
                normalized_path,
            )

            self.increment_throttle(client_ip)

            # the platform's ordinary 404, so that a blocked path looks like any missing one.
            return response_for_exception(request, Http404())

        return None

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize a request path, to defeat traversal and encoding bypasses.

        The path is url-decoded twice, NFKC-normalized, its backslashes turned into slashes, its
        null bytes removed, its repeated slashes collapsed, its traversal resolved, and lower-cased.

        :param path: The raw request path.
        :returns: The normalized path, which always starts with ``/``.
        """

        for _ in range(2):
            path = urllib.parse.unquote(path)

        path = unicodedata.normalize("NFKC", path)

        path = path.replace("\\", "/")
        path = path.replace("\x00", "")

        path = REPEATED_SLASHES.sub("/", path)

        path = posixpath.normpath(path)

        if not path.startswith("/"):
            path = f"/{path}"

        return path.lower()

    def is_amnesty_path(self, path: str) -> bool:
        """
        Return whether a path is exempt from the sensitive-file check.

        A path is exempt when it is an amnesty url, or when it or one of its segments matches an
        allowed pattern.

        :param path: The normalized request path.
        :returns: True if the path is exempt.
        """
        if path.replace("/", "") in self.amnesty_urls:
            return True

        if not self.allowed_patterns:
            return False

        if any(pattern.match(path) for pattern in self.allowed_patterns):
            return True

        for segment in self.iter_path_segments(path):
            for pattern in self.allowed_patterns:
                if pattern.match(segment):
                    return True
        return False

    def is_throttled(self, client_ip: str) -> bool:
        """
        Return whether a client has reached the throttle limit of sensitive-file probes.

        :param client_ip: The client's ip address.
        :returns: True if the client's count, in the cache, is at least ``THROTTLE_LIMIT``.
        """
        throttle_key = self.get_throttle_key(client_ip)

        blocked_count = cache.get(throttle_key, 0)

        return blocked_count >= self.THROTTLE_LIMIT

    def increment_throttle(self, client_ip: str) -> None:
        """
        Add one to a client's probe count in the cache, and reset its ``THROTTLE_TIMEOUT``.

        :param client_ip: The client's ip address.
        """
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
        """
        Return the cache key of a client's probe count.

        :param client_ip: The client's ip address.
        :returns: The cache key.
        """
        return f"sensitive_files_throttle:{client_ip}"

    @staticmethod
    def iter_path_segments(path: str) -> Iterable[str]:
        """
        Return the non-empty segments of a path, e.g. ``a`` and ``b`` for ``/a//b/``.

        :param path: The path.
        :returns: A generator of the segments.
        """
        return (segment for segment in path.split("/") if segment)

    @classmethod
    def is_sensitive_request(cls, path: str) -> bool:
        """
        Return whether a normalized path asks for a sensitive file.

        :param path: The normalized request path.
        :returns: True if the path, or one of its segments, is a sensitive file.
        """
        is_sensitive = is_sensitive_path(path)
        return is_sensitive


@lru_cache(maxsize=SENSITIVE_PATH_CACHE_SIZE)
def is_sensitive_path(path: str) -> bool:
    """
    Return whether a normalized path, or one of its segments, matches a sensitive file.

    The path matches when it, or a segment of it, is one of :data:`EXACT_MATCHES`, or matches
    :data:`GLOB_REGEX`. It is pure, so each process remembers the most recent results.

    :param path: The normalized request path.
    :returns: True if the path is sensitive.
    """
    normalized_full_path = path.lstrip("/")
    if normalized_full_path in EXACT_MATCHES:
        return True
    if GLOB_REGEX.match(normalized_full_path):
        return True

    for segment in path.split("/"):
        if not segment:
            continue
        if segment in EXACT_MATCHES:
            return True
        if GLOB_REGEX.match(segment):
            return True

    return False
