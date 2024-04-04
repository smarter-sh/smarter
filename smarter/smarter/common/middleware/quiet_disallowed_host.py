# -*- coding: utf-8 -*-
"""This module is used to suppress DisallowedHost exception and return HttpResponseBadRequest instead."""
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseBadRequest


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
