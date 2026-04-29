"""
Middleware to set a unique job ID for each request's logging context.
"""

from contextvars import Token
from typing import Awaitable

from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterMiddlewareMixin

from .redis_log_handler import get_user_context, job_id_factory, user_id_context


class SmarterRequestLogContextMiddleware(SmarterMiddlewareMixin):
    """
    Middleware to set a unique job ID for each request's logging context.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:
        """
        Set a unique job ID for this request's logging context.
        """
        if hasattr(request, "user") and request.user.is_authenticated:
            context = get_user_context(request.user)
        else:
            context = job_id_factory()

        token: Token = user_id_context.set(context)
        try:
            response = self.get_response(request)
        finally:
            user_id_context.reset(token)
        return response
