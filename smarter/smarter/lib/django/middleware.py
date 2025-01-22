"""This module is used to suppress DisallowedHost exception and return HttpResponseForbidden instead."""

from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


class BlockSensitiveFilesMiddleware(MiddlewareMixin):
    """Block requests for common sensitive files."""

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
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
        }

    def __call__(self, request):
        if any(sensitive_file in request.path for sensitive_file in self.sensitive_files):
            return HttpResponseForbidden()
        return self.get_response(request)
