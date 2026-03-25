"""
Module: smarter.common.utils.is_authenticated_request
"""

import logging
from typing import TYPE_CHECKING, Optional, Union

from smarter.common.helpers.console_helpers import formatted_text

from .uri import smarter_build_absolute_uri

if TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest
    from django.http import HttpRequest
    from rest_framework.request import Request

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__)
RequestType = Union["HttpRequest", "Request", "WSGIRequest"]


def is_authenticated_request(request: Optional[RequestType]) -> bool:
    """
    Determines whether the provided request is authenticated. Provides extensive logging for debugging purposes.

    :param request: The request object to check. This can be an instance of :class:`django.http.HttpRequest`, :class:`rest_framework.request.Request`, or :class:`django.core.handlers.wsgi.WSGIRequest`. If ``None`` is provided, the function will return ``False``.

    :type request: Optional[Union[HttpRequest, Request, WSGIRequest]]

    :return: Returns ``True`` if the request is authenticated (i.e., the request has a ``user`` attribute and ``user.is_authenticated`` is ``True``). Returns ``False`` otherwise.
    :rtype: bool

    :raises Exception: Any unexpected error during attribute access will be caught and logged; the function will return ``False`` in such cases.

    .. note::
        This function is compatible with Django and Django REST Framework request objects. It also supports WSGIRequest and can be used in unit tests with mock objects that have the required attributes.

    .. warning::
        If the request object does not have a ``user`` attribute, or if ``user.is_authenticated`` is not available, the function will return ``False``. Any exceptions are logged as warnings.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import is_authenticated_request
        from django.http import HttpRequest

        request = HttpRequest()
        request.user = SomeUserObject()
        authenticated = is_authenticated_request(request)
        print(authenticated)  # True or False depending on user.is_authenticated

    .. code-block:: python

        # Example with DRF Request
        from rest_framework.request import Request

        drf_request = Request(...)
        authenticated = is_authenticated_request(drf_request)
        print(authenticated)
    """
    logger.debug("%s.is_authenticated_request()", logger_prefix)
    try:
        # pylint: disable=import-outside-toplevel
        from django.core.handlers.wsgi import WSGIRequest
        from django.http import HttpRequest
        from rest_framework.request import Request

        is_valid_request_object = isinstance(request, (HttpRequest, Request, WSGIRequest))
        if is_valid_request_object:
            logger.debug(
                "%s.is_authenticated_request() Valid request object of type %s",
                logger_prefix,
                type(request),
            )
        else:
            # suggests buggy code, hence the warning
            logger.warning(
                "%s.is_authenticated_request() Invalid request object of type %s - returning False",
                logger_prefix,
                type(request),
            )
            return False

        has_user = hasattr(request, "user")
        if has_user:
            logger.debug(
                "%s.is_authenticated_request() Request has 'user' attribute of type %s",
                logger_prefix,
                type(request.user),
            )
        else:
            logger.debug(
                "%s.is_authenticated_request() Request does not have 'user' attribute - returning False",
                logger_prefix,
            )

        has_is_authenticated = has_user and hasattr(request.user, "is_authenticated")
        if has_is_authenticated:
            logger.debug(
                "%s.is_authenticated_request() Request.user has 'is_authenticated' attribute",
                logger_prefix,
            )
        else:
            # this should not happen in normal code, hence the warning
            logger.warning(
                "%s.is_authenticated_request() Request.user of type %s does not have 'is_authenticated' attribute - returning False",
                logger_prefix,
                type(request.user),
            )

        url = smarter_build_absolute_uri(request)
        if is_valid_request_object and has_user and has_is_authenticated:
            retval = request.user.is_authenticated
            logger.debug(
                "%s.is_authenticated_request() Request is_authenticated: %s URL: %s",
                logger_prefix,
                retval,
                url,
            )
        else:
            retval = False
            logger.debug(
                "%s.is_authenticated_request() Request is not authenticated - returning False URL: %s",
                logger_prefix,
                url,
            )
        return retval

    # pylint: disable=W0718
    except Exception as e:
        logger.error("%s.is_authenticated_request() failed: %s", logger_prefix, formatted_text(str(e)))
        return False


__all__ = ["is_authenticated_request"]
