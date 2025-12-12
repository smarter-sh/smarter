"""This module is used to suppress DisallowedHost exception and return HttpResponseForbidden instead."""

import fnmatch
import logging
import re

from django.conf import settings
from django.http import HttpResponseForbidden

from smarter.common.classes import SmarterMiddlewareMixin
from smarter.common.conf import settings as smarter_settings
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SmarterBlockSensitiveFilesMiddleware(SmarterMiddlewareMixin):
    """
    Middleware to return HttpResponseForbidden for common sensitive files, regardless of whether these
    do or do not exist. This is a countermeasure against simple, brute-force attacks
    and automated 'bot' clients probing for sensitive files. This middleware works from a static list
    of common sensitive files and patterns, returning a 403 Forbidden response for requests matching these files.

    This middleware inspects incoming HTTP requests and blocks access to files and paths that are commonly
    targeted by attackers or bots, such as configuration files, environment files, backup files, and private keys.
    If a client attempts to access these files more than a configurable threshold within a time window, their
    requests are throttled and further attempts are blocked with a 403 Forbidden response.

    The middleware also supports an "amnesty" mechanism, allowing certain patterns to bypass blocking, and
    provides detailed logging for all blocking and throttling events.

    :cvar int THROTTLE_LIMIT: The maximum number of blocked sensitive file requests allowed from a single client IP within the timeout period before blocking is triggered. Default is 5.
    :cvar int THROTTLE_TIMEOUT: The duration of the timeout window in seconds during which blocked requests are counted and blocking is enforced. Default is 600 seconds (10 minutes).
    :cvar allowed_patterns: Patterns for which requests are granted amnesty and not blocked, even if they match sensitive files.
    :vartype allowed_patterns: tuple
    :cvar sensitive_files: Set of filenames and patterns considered sensitive and subject to blocking.
    :vartype sensitive_files: set

    **Key Features**

    - Blocks requests for a comprehensive list of sensitive files and file patterns.
    - Throttles repeated attempts from the same client IP and blocks further requests after a threshold.
    - Supports amnesty patterns to allow exceptions for specific paths.
    - Provides detailed logging for all blocking, throttling, and amnesty events.
    - Integrates with Django's cache for tracking request counts and with application logging.

    .. note::
        - Amnesty patterns can be configured via the ``SMARTER_SENSITIVE_FILES_AMNESTY_PATTERNS`` Django setting.
        - Logging is controlled via a waffle switch and the application's log level.
        - The client IP is determined using the :meth:`get_client_ip` method.

    **Example**

    To enable this middleware, add it to your Django project's middleware settings::

        MIDDLEWARE = [
            ...
            'smarter.lib.django.middleware.sensitive_files.SmarterBlockSensitiveFilesMiddleware',
            ...
        ]

    :param get_response: The next middleware or view in the Django request/response chain.
    :type get_response: callable

    :returns: The HTTP response object, or a 403 Forbidden response if the request is blocked.
    :rtype: django.http.HttpResponse or django.http.HttpResponseForbidden
    """

    THROTTLE_LIMIT = 5
    THROTTLE_TIMEOUT = 600  # seconds (10 minutes)

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

        # grant amnesty for specific patterns
        self.allowed_patterns = [
            re.compile(pattern) for pattern in getattr(settings, "SMARTER_SENSITIVE_FILES_AMNESTY_PATTERNS", [])
        ]
        self.sensitive_files = {
            ".env",
            "config.php",
            "wp-config.php",
            "settings.py",
            ".bak",
            ".tmp",
            ".swp",
            ".git",
            ".svn",
            "id_rsa",
            "id_dsa",
            ".DS_Store",
            "login.action",
            ".vscode",
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
            "Gemfile",
            "Gemfile.lock",
            "Pipfile",
            "Pipfile.lock",
            "requirements.txt",
            "credentials.json",
            "secrets.json",
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
            "ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application",
        }

    def __call__(self, request):
        request_path = request.path.lower()
        if request_path.replace("/", "") in self.amnesty_urls:
            logger.info("%s amnesty granted to: %s", self.formatted_class_name, request.path)
            return self.get_response(request)

        for pattern in self.allowed_patterns:
            if pattern.match(request_path):
                logger.info(
                    "%s amnesty granted to: %s because it matches an allowed pattern in settings.SMARTER_SENSITIVE_FILES_AMNESTY_PATTERNS",
                    self.formatted_class_name,
                    request.path,
                )
                return self.get_response(request)

        client_ip = self.get_client_ip(request)
        if not client_ip:
            return self.get_response(request)

        # Throttle check
        throttle_key = f"sensitive_files_throttle:{client_ip}"
        blocked_count = cache.get(throttle_key, 0)
        if blocked_count >= self.THROTTLE_LIMIT:
            logger.warning(
                "%s Throttled client %s after %d blocked requests", self.formatted_class_name, client_ip, blocked_count
            )
            return HttpResponseForbidden(
                "You have been blocked due to too many suspicious requests from your IP. Try again later or contact support@smarter.sh."
            )

        path_basename = request_path.rsplit("/", 1)[-1]
        for sensitive_file in self.sensitive_files:
            sensitive_file = sensitive_file.lower()
            if (
                fnmatch.fnmatch(path_basename, sensitive_file)
                or fnmatch.fnmatch(request_path, sensitive_file)
                or sensitive_file in request_path
            ):
                logger.warning("%s Blocked request for sensitive file: %s", self.formatted_class_name, request.path)

                try:
                    blocked_count = cache.incr(throttle_key)
                except ValueError:
                    cache.set(throttle_key, 1, timeout=self.THROTTLE_TIMEOUT)
                    blocked_count = 1
                else:
                    cache.set(throttle_key, blocked_count, timeout=self.THROTTLE_TIMEOUT)
                return HttpResponseForbidden(
                    "Your request has been blocked by Smarter. Contact support@smarter.sh for assistance."
                )
        return self.get_response(request)
