# -*- coding: utf-8 -*-
"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseBadRequest, HttpResponseForbidden


class QuietDisallowedHostMiddleware:
    """Suppress DisallowedHost exception and return HttpResponseBadRequest instead."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except DisallowedHost:
            return HttpResponseBadRequest()

        return response


class BlockSensitiveFilesMiddleware:
    """Block requests for common sensitive files."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.sensitive_files = [
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
        ]

    def __call__(self, request):
        for sensitive_file in self.sensitive_files:
            if sensitive_file in request.path:
                return HttpResponseForbidden()
        return self.get_response(request)
