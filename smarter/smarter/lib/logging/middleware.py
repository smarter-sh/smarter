"""
Middleware to set a unique job ID for each request's logging context.
"""

from contextvars import Token
from typing import Awaitable

from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterMiddlewareMixin

from .redis_log_handler import job_id_context, job_id_factory


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
        job_id: str = job_id_factory(prefix=request.__class__.__name__)
        token: Token = job_id_context.set(job_id)
        try:
            response = self.get_response(request)
        finally:
            job_id_context.reset(token)
        return response
