"""This module is used to suppress DisallowedHost exception and return HttpResponseForbidden instead."""

import fnmatch
import logging
import re
import urllib.parse

from django.http import HttpResponseForbidden

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.lib.cache import cache_results
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

logger.debug("Loading %s", formatted_text(__name__ + ".SmarterBlockSensitiveFilesMiddleware"))

ALLOWED_PATTERNS = [re.compile(pattern) for pattern in smarter_settings.sensitive_files_amnesty_patterns]
SENSITIVE_FILES = list(
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
)


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
        - Amnesty patterns can be configured via the ``smarter_settings.sensitive_files_amnesty_patterns`` Django setting.
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

    @property
    def formatted_class_name(self) -> str:
        """Return the formatted class name for logging purposes."""
        return formatted_text(f"{__name__}.{SmarterBlockSensitiveFilesMiddleware.__name__}")

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

        # grant amnesty for specific patterns
        self.allowed_patterns = ALLOWED_PATTERNS
        self.sensitive_files = SENSITIVE_FILES

    def __call__(self, request):
        if not waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_SENSITIVE_FILES):
            return self.get_response(request)

        request_path = request.path.lower()
        if request_path.replace("/", "") in self.amnesty_urls:
            logger.info("%s amnesty granted to: %s", self.formatted_class_name, request.path)
            return self.get_response(request)

        for pattern in self.allowed_patterns:
            if pattern.match(request_path):
                logger.info(
                    "%s amnesty granted to: %s because it matches an allowed pattern in settings.smarter_settings.sensitive_files_amnesty_patterns",
                    self.formatted_class_name,
                    request.path,
                )
                return self.get_response(request)

        client_ip = self.get_client_ip(request)
        if not client_ip:
            client_ip = "unknown-ip"

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

        @cache_results(timeout=60 * 60 * 24)
        def cached_security_check_by_url(path) -> bool:
            parsed_url = urllib.parse.urlparse(path)
            path = parsed_url.path.lower()
            # Split path into segments, ignore empty strings
            path_parts = [part for part in path.split("/") if part]

            logger.debug("%s Performing cached security check for path: %s", self.formatted_class_name, path)
            logger.debug("%s Path parts for checking: %s", self.formatted_class_name, path_parts)

            # Check amnesty patterns on each part of the path
            for part in path_parts:
                for pattern in self.allowed_patterns:
                    if pattern.match(part):
                        logger.info(
                            "%s amnesty granted to: %s because part '%s' matches an allowed pattern in settings.smarter_settings.sensitive_files_amnesty_patterns",
                            self.formatted_class_name,
                            request.path,
                            part,
                        )
                        return True

            # Check sensitive files on each part of the path
            for part in path_parts:
                for sensitive_file in self.sensitive_files:
                    sensitive_file = sensitive_file.lower()
                    if fnmatch.fnmatch(part, sensitive_file):
                        logger.warning(
                            "%s Detected sensitive file match: %s in path: %s",
                            self.formatted_class_name,
                            sensitive_file,
                            request.path,
                        )
                        return False

            return True

        if cached_security_check_by_url(request_path):
            return self.get_response(request)

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
