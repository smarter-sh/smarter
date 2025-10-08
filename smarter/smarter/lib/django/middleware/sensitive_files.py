"""This module is used to suppress DisallowedHost exception and return HttpResponseForbidden instead."""

import fnmatch
import ipaddress
import logging
import re

from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from smarter.common.classes import SmarterHelperMixin


logger = logging.getLogger(__name__)


class BlockSensitiveFilesMiddleware(MiddlewareMixin, SmarterHelperMixin):
    """Block requests for common sensitive files."""

    THROTTLE_LIMIT = 5
    THROTTLE_TIMEOUT = 600  # seconds (10 minutes)

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

        # grant amnesty for specific patterns
        self.allowed_patterns = [
            re.compile(r"^/dashboard/account/password-reset-link/[^/]+/[^/]+/$"),
            re.compile(r"^/api(/.*)?$"),
            re.compile(r"^/admin(/.*)?$"),
            re.compile(r"^/plugin(/.*)?$"),
            re.compile(r"^/docs/manifest(/.*)?$"),
            re.compile(r"^/docs/json-schema(/.*)?$"),
            re.compile(r".*stackademy.*"),
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

    def get_client_ip(self, request):
        """Get client IP address from request."""
        # Check for real IP from various proxy headers in order of preference
        for header in ["HTTP_X_REAL_IP", "HTTP_X_FORWARDED_FOR", "HTTP_CF_CONNECTING_IP"]:
            ip = request.META.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first (original client)
                if header == "HTTP_X_FORWARDED_FOR":
                    ip = ip.split(",")[0].strip()
                # Skip internal/private IP ranges (Kubernetes pods, load balancers)
                if not self._is_private_ip(ip.strip()):
                    return ip.strip()

        # Fallback to REMOTE_ADDR (should not be used in production behind proxies)
        return request.META.get("REMOTE_ADDR", "127.0.0.1")

    def _is_private_ip(self, ip):
        """Check if IP is in private/internal ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError:
            # Invalid IP format
            return True

    def __call__(self, request):
        request_path = request.path.lower()
        client_ip = self.get_client_ip(request)

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
                        logger.info("%s amnesty granted to: %s", self.formatted_class_name, request.path)
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
