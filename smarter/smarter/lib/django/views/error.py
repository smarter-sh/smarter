# pylint: disable=C0115,W1113
"""
Default error views for Django.
"""

from http import HTTPStatus

from django.http import HttpResponse
from django.shortcuts import render


class SmarterHttpResponseErrorBase(HttpResponse):
    template_file: str = ""
    context: dict = {}

    def __init__(self, request, error_message: str, *args, **kwargs):
        error_message = error_message or "Something went wrong! Please try again later."
        self.context = {"message": error_message}
        content = render(request, self.template_file, self.context).content
        super().__init__(content, *args, **kwargs)


class SmarterHttpResponseBadRequest(SmarterHttpResponseErrorBase):
    def __init__(self, request, error_message: str = None, *args, **kwargs):
        error_message = error_message or "Dohhhh, that's a bad request my friend."
        self.template_file = "400.html"
        self.status_code = 400  # HTTPStatus.BAD_REQUEST
        super().__init__(request=request, error_message=error_message, *args, **kwargs)


class SmarterHttpResponseForbidden(SmarterHttpResponseErrorBase):
    def __init__(self, request, error_message: str = None, *args, **kwargs):
        error_message = error_message or "Awe shucks, you're not allowed to do that."
        self.template_file = "403.html"
        self.status_code = 403  # HTTPStatus.FORBIDDEN
        super().__init__(request=request, error_message=error_message, *args, **kwargs)


class SmarterHttpResponseNotFound(SmarterHttpResponseErrorBase):
    def __init__(self, request, error_message: str = None, *args, **kwargs):
        error_message = error_message or "Oh no!!! We couldn't find that page."
        self.template_file = "404.html"
        self.status_code = 404  # HTTPStatus.NOT_FOUND
        super().__init__(request=request, error_message=error_message, *args, **kwargs)


class SmarterHttpResponseServerError(SmarterHttpResponseErrorBase):
    def __init__(self, request, error_message: str = None, *args, **kwargs):
        self.template_file = "500.html"
        self.status_code = 500  # HTTPStatus.INTERNAL_SERVER_ERROR
        super().__init__(request=request, error_message=error_message, *args, **kwargs)
