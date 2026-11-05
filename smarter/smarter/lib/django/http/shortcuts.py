# pylint: disable=C0115,W1113
"""
Smarter's html responses, which render an error or information page.

These are wrappers around the Django HttpResponse class,
with a custom error_message attribute for the custom templates, and default error messages.
"""

from http import HTTPStatus
from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from smarter.lib.typing import SmarterDictType


class SmarterHttpResponse(HttpResponse):
    """
    A generic HTTP response class for Smarter applications, extending Django's ``HttpResponse``.

    This class is designed to render a specified template with a customizable error message and HTTP status code.
    It is intended to standardize error handling and response rendering across Smarter Django views.

    :param request: The Django ``HttpRequest`` object associated with the response.
    :param error_message: An optional custom error message to display in the rendered template. If not provided, a default message is used.
    :param status_code: The HTTP status code for the response. Defaults to 200 (OK).
    :param template_file: The name of the Django template file to render. Defaults to ``"200.html"``.
    :param args: Additional positional arguments passed to the parent ``HttpResponse``.
    :param kwargs: Additional keyword arguments passed to the parent ``HttpResponse``. The ``content_type`` is set to ``"text/html"`` by default.

    **Context:**

    The template is rendered with a context dictionary containing a single key:

    - ``message``: The error message to display.

    **Example Usage:**

    .. code-block:: python

        from smarter.lib.django.http.shortcuts import SmarterHttpResponse

        def my_view(request):
            # Custom error message and template
            return SmarterHttpResponse(
                request,
                error_message="Custom error occurred.",
                status_code=400,
                template_file="400.html"
            )

    **Notes:**

    - This class is intended for use in Django views where a standardized error or informational response is required.
    - The ``template_file`` should exist in your Django templates directory and be designed to display the ``message`` context variable.

    **Warning:**

    - If the specified template file does not exist, Django will raise a ``TemplateDoesNotExist`` exception.
    - The default error message is generic; always provide a specific message for better user experience.
    """

    status_code: int
    context: SmarterDictType = {}

    def __init__(
        self,
        request: HttpRequest,
        error_message: Optional[str] = None,
        status_code: int = HTTPStatus.OK.value,
        template_file: str = "200.html",
        *args,
        **kwargs,
    ):
        kwargs.setdefault("content_type", "text/html")
        self.status_code: int = status_code
        if not error_message:
            error_message = "Something went wrong! Please try again later."
        self.context = {"message": error_message}
        rendered = render(request=request, template_name=template_file, context=self.context)
        content = rendered.content
        super().__init__(content=content, *args, **kwargs)


class SmarterHttpErrorResponse(SmarterHttpResponse):
    """
    Base class of the Smarter html error responses, e.g. :class:`SmarterHttpResponseBadRequest`.

    It adds nothing to :class:`SmarterHttpResponse`; it lets callers tell an error page from a normal one.
    """


class SmarterHttpResponseBadRequest(SmarterHttpErrorResponse):
    """
    Specialized HTTP 400 (Bad Request) response for Smarter Django applications.

    This class extends :class:`SmarterHttpErrorResponse` to provide a standardized way to return
    a "Bad Request" response, rendering the ``400.html`` template with a customizable error message.

    :param request: The Django ``HttpRequest`` object associated with the response.
    :param error_message: An optional custom error message to display in the rendered template.
        If not provided, a default message is used: "Dohhhh, that's a bad request my friend."
    :param args: Additional positional arguments passed to the parent ``SmarterHttpErrorResponse``.
    :param kwargs: Additional keyword arguments passed to the parent ``SmarterHttpErrorResponse``.

    **Context:**

    The template is rendered with a context dictionary containing:

    - ``message``: The error message to display.

    **Example Usage:**

    .. code-block:: python

        from smarter.lib.django.http.shortcuts import SmarterHttpResponseBadRequest

        def my_view(request):
            if not request.GET.get("important_param"):
                return SmarterHttpResponseBadRequest(
                    request,
                    error_message="Missing required parameter: important_param"
                )
            # ... rest of the view logic ...

    **Notes:**

    - The ``400.html`` template should exist in your Django templates directory and be designed to display the ``message`` context variable.
    - This class is intended for use in views where you want to provide a user-friendly error page for bad requests.

    **Warning:**

    - If the specified template file does not exist, Django will raise a ``TemplateDoesNotExist`` exception.
    - Always provide a clear error message to help users understand what went wrong.
    """

    def __init__(self, request: HttpRequest, error_message: Optional[str] = None, *args, **kwargs):
        status_code: int = HTTPStatus.BAD_REQUEST.value
        if not error_message:
            error_message = "Dohhhh, that's a bad request my friend."
        template_file = "400.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )


class SmarterHttpResponseForbidden(SmarterHttpErrorResponse):
    """
    Specialized HTTP 403 (Forbidden) response for Smarter Django applications.

    This class extends :class:`SmarterHttpErrorResponse` to provide a standardized way to return
    a "Forbidden" response, rendering the ``403.html`` template with a customizable error message.

    :param request: The Django ``HttpRequest`` object associated with the response.
    :param error_message: An optional custom error message to display in the rendered template.
        If not provided, a default message is used: "Awe shucks, you're not allowed to do that."
    :param args: Additional positional arguments passed to the parent ``SmarterHttpErrorResponse``.
    :param kwargs: Additional keyword arguments passed to the parent ``SmarterHttpErrorResponse``.

    **Context:**

    The template is rendered with a context dictionary containing:

    - ``message``: The error message to display.

    **Example Usage:**

    .. code-block:: python

        from smarter.lib.django.http.shortcuts import SmarterHttpResponseForbidden

        def my_view(request):
            if not request.user.has_perm("myapp.can_access"):
                return SmarterHttpResponseForbidden(
                    request,
                    error_message="You do not have permission to access this resource."
                )
            # ... rest of the view logic ...

    **Notes:**

    - The ``403.html`` template should exist in your Django templates directory and be designed to display the ``message`` context variable.
    - This class is intended for use in views where you want to provide a user-friendly error page for forbidden actions.

    **Warning:**

    - If the specified template file does not exist, Django will raise a ``TemplateDoesNotExist`` exception.
    - Always provide a clear error message to help users understand why access was denied.
    """

    def __init__(self, request: HttpRequest, error_message: Optional[str] = None, *args, **kwargs):
        status_code: int = HTTPStatus.FORBIDDEN.value
        if not error_message:
            error_message = "Awe shucks, you're not allowed to do that."
        template_file = "403.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )


class SmarterHttpResponseNotFound(SmarterHttpErrorResponse):
    """
    Specialized HTTP 404 (Not Found) response for Smarter Django applications.

    This class extends :class:`SmarterHttpErrorResponse` to provide a standardized way to return
    a "Not Found" response, rendering the ``404.html`` template with a customizable error message.

    :param request: The Django ``HttpRequest`` object associated with the response.
    :param error_message: An optional custom error message to display in the rendered template.
        If not provided, a default message is used: "Oh no!!! We couldn't find that page."
    :param args: Additional positional arguments passed to the parent ``SmarterHttpErrorResponse``.
    :param kwargs: Additional keyword arguments passed to the parent ``SmarterHttpErrorResponse``.

    **Context:**

    The template is rendered with a context dictionary containing:

    - ``message``: The error message to display.

    **Example Usage:**

    .. code-block:: python

        from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound

        def my_view(request):
            obj = get_object_or_404(MyModel, pk=some_id)
            if not obj:
                return SmarterHttpResponseNotFound(
                    request,
                    error_message="The requested object does not exist."
                )
            # ... rest of the view logic ...

    **Notes:**

    - The ``404.html`` template should exist in your Django templates directory and be designed to display the ``message`` context variable.
    - This class is intended for use in views where you want to provide a user-friendly error page for missing resources.

    **Warning:**

    - If the specified template file does not exist, Django will raise a ``TemplateDoesNotExist`` exception.
    - Always provide a clear error message to help users understand what could not be found.
    """

    def __init__(self, request: HttpRequest, error_message: Optional[str] = None, *args, **kwargs):
        status_code: int = HTTPStatus.NOT_FOUND.value
        if not error_message:
            error_message = "Oh no!!! We couldn't find that page."
        template_file = "404.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )


class SmarterHttpResponseServerError(SmarterHttpErrorResponse):
    """
    Specialized HTTP 500 (Internal Server Error) response for Smarter Django applications.

    This class extends :class:`SmarterHttpErrorResponse` to provide a standardized way to return
    an "Internal Server Error" response, rendering the ``500.html`` template with a customizable error message.

    :param request: The Django ``HttpRequest`` object associated with the response.
    :param error_message: An optional custom error message to display in the rendered template.
        If not provided, a default message is used: "Ugh!!! Something went wrong on our end."
    :param args: Additional positional arguments passed to the parent ``SmarterHttpErrorResponse``.
    :param kwargs: Additional keyword arguments passed to the parent ``SmarterHttpErrorResponse``.

    **Context:**

    The template is rendered with a context dictionary containing:

    - ``message``: The error message to display.

    **Example Usage:**

    .. code-block:: python

        from smarter.lib.django.http.shortcuts import SmarterHttpResponseServerError

        def my_view(request):
            try:
                # ... some logic that may raise an exception ...
                pass
            except Exception:
                logger.exception("%s.my_view() failed", logger_prefix)
                return SmarterHttpResponseServerError(
                    request,
                    error_message="An unexpected error occurred."
                )

    **Notes:**

    - The ``500.html`` template should exist in your Django templates directory and be designed to display the ``message`` context variable.
    - This class is intended for use in views where you want to provide a user-friendly error page for server errors.

    **Warning:**

    - If the specified template file does not exist, Django will raise a ``TemplateDoesNotExist`` exception.
    - Always provide a clear error message to help users understand that a server error has occurred.
    """

    def __init__(self, request: HttpRequest, error_message: Optional[str] = None, *args, **kwargs):
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
        if not error_message:
            error_message = "Ugh!!! Something went wrong on our end."
        template_file = "500.html"
        super().__init__(
            request=request,
            error_message=error_message,
            status_code=status_code,
            template_file=template_file,
            *args,
            **kwargs,
        )
