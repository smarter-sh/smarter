"""
Middleware to set a unique job ID for each request's logging context.
"""

from smarter.common.mixins import SmarterMiddlewareMixin

from .redis_log_handler import current_job_id, job_id_factory


class SmarterRequestLogContextMiddleware(SmarterMiddlewareMixin):
    """
    Middleware to set a unique job ID for each request's logging context.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def __call__(self, request):
        # Set a unique job ID for this request's context
        token = current_job_id.set(job_id_factory("request"))
        try:
            response = self.get_response(request)
        finally:
            current_job_id.reset(token)  # clean up after the request
        return response
