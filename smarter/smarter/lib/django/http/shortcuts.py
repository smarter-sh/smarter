# pylint: disable=C0115,W1113
"""
Smarter http responses. these are wrappers around the Django HttpResponse class,
with a custom error_message attribute for the custom templates, and default error messages.
"""

from http import HTTPStatus

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render


class SmarterHttpResponse(HttpResponse):
    """
    Smarter generic http response class. Maps a smarter django template and custom
    error message to the response.
    """

    status_code: int
    context: dict = {}

    def __init__(
        self,
        request: WSGIRequest,
        error_message: str = None,
        status_code: int = HTTPStatus.OK.value,
        template_file: str = "200.html",
        *args,
        **kwargs,
    ):
        kwargs: dict = kwargs or {}
        kwargs.setdefault("content_type", "text/html")
        self.status_code: int = status_code
        error_message = error_message or "Something went wrong! Please try again later."
        self.context = {"message": error_message}
        content = render(request=request, template_name=template_file, context=self.context).content
        super().__init__(content=content, *args, **kwargs)


class SmarterHttpResponseBadRequest(SmarterHttpResponse):
    def __init__(self, request: WSGIRequest, error_message: str = None, *args, **kwargs):
        status_code: int = HTTPStatus.BAD_REQUEST.value
        error_message = error_message or "Dohhhh, that's a bad request my friend."
        template_file = "400.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )


class SmarterHttpResponseForbidden(SmarterHttpResponse):
    def __init__(self, request: WSGIRequest, error_message: str = None, *args, **kwargs):
        status_code: int = HTTPStatus.FORBIDDEN.value
        error_message = error_message or "Awe shucks, you're not allowed to do that."
        template_file = "403.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )


class SmarterHttpResponseNotFound(SmarterHttpResponse):
    def __init__(self, request: WSGIRequest, error_message: str = None, *args, **kwargs):
        status_code: int = HTTPStatus.NOT_FOUND.value
        error_message = error_message or "Oh no!!! We couldn't find that page."
        template_file = "404.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )


class SmarterHttpResponseServerError(SmarterHttpResponse):
    def __init__(self, request: WSGIRequest, error_message: str = None, *args, **kwargs):
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
        error_message = error_message or "Ugh!!! Something went wrong on our end."
        template_file = "500.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )
