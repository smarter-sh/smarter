"""This module is used to suppress DisallowedHost exception and return HttpResponseForbidden instead."""

import fnmatch
import logging
import re

from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from smarter.common.classes import SmarterHelperMixin


logger = logging.getLogger(__name__)


class BlockSensitiveFilesMiddleware(MiddlewareMixin, SmarterHelperMixin):
    """Block requests for common sensitive files."""

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

        # Check for sensitive files using glob patterns
        path_basename = request_path.rsplit("/", 1)[-1]
        for sensitive_file in self.sensitive_files:
            sensitive_file = sensitive_file.lower()
            if (
                fnmatch.fnmatch(path_basename, sensitive_file)
                or fnmatch.fnmatch(request_path, sensitive_file)
                or sensitive_file in request_path  # fallback for legacy entries
            ):
                # Allow specific patterns to pass through
                for pattern in self.allowed_patterns:
                    if pattern.match(request_path):
                        logger.info("%s amnesty granted to: %s", self.formatted_class_name, request.path)
                        return self.get_response(request)

                logger.warning("%s Blocked request for sensitive file: %s", self.formatted_class_name, request.path)
                return HttpResponseForbidden(
                    "Your request has been blocked by Smarter. Contact support@smarter.sh for assistance."
                )
        return self.get_response(request)
