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
        }

    def __call__(self, request):
        if any(sensitive_file in request.path for sensitive_file in self.sensitive_files):
            return HttpResponseForbidden()
        return self.get_response(request)
