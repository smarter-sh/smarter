"""This module is used to suppress DisallowedHost exception and return HttpResponseForbidden instead."""

import fnmatch
import logging
import re

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden

from smarter.common.classes import SmarterMiddlewareMixin
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class BlockSensitiveFilesMiddleware(SmarterMiddlewareMixin):
    """Block requests for common sensitive files."""

    THROTTLE_LIMIT = 5
    THROTTLE_TIMEOUT = 600  # seconds (10 minutes)

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

        # grant amnesty for specific patterns
        self.allowed_patterns = (
            settings.SENSITIVE_FILES_AMNESTY_PATTERNS if hasattr(settings, "SENSITIVE_FILES_AMNESTY_PATTERNS") else []
        )
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
            logger.debug("%s amnesty granted to: %s", self.formatted_class_name, request.path)
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
                for pattern in self.allowed_patterns:
                    if pattern.match(request_path):
                        logger.debug("%s amnesty granted to: %s", self.formatted_class_name, request.path)
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
        return self.get_response(request)
