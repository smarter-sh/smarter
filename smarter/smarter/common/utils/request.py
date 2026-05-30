"""
smarter.common.utils.request
=============================

Helpers for request authentication detection in Django and DRF.

This module provides the ``is_authenticated_request`` function, which determines whether a given
request object is authenticated. It supports Django's ``HttpRequest``, Django REST Framework's ``Request``,
and ASGIRequest types, and provides extensive logging for debugging and auditing purposes.

**Example usage:**

.. code-block:: python

    from smarter.common.utils import is_authenticated_request
    from django.http import HttpRequest

    request = HttpRequest()
    request.user = SomeUserObject()
    authenticated = is_authenticated_request(request)
    print(authenticated)  # True or False depending on user.is_authenticated

"""

import random
from typing import TYPE_CHECKING, Optional, Union

from smarter.common.const import SMARTER_IS_INTERNAL_API_REQUEST
from smarter.lib import logging

from .uri import smarter_build_absolute_uri

if TYPE_CHECKING:
    from django.core.handlers.asgi import ASGIRequest
    from django.http import HttpRequest
    from rest_framework.request import Request

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)
RequestType = Union["HttpRequest", "Request", "ASGIRequest"]


def is_authenticated_request(request: Optional[RequestType]) -> bool:
    """
    Determines whether the provided request is authenticated. Provides extensive logging for debugging purposes.

    :param request: The request object to check. This can be an instance of :class:`django.http.HttpRequest`, :class:`rest_framework.request.Request`, or :class:`django.core.handlers.wsgi.ASGIRequest`. If ``None`` is provided, the function will return ``False``.

    :type request: Optional[Union[HttpRequest, Request, ASGIRequest]]

    :return: Returns ``True`` if the request is authenticated (i.e., the request has a ``user`` attribute and ``user.is_authenticated`` is ``True``). Returns ``False`` otherwise.
    :rtype: bool

    :raises Exception: Any unexpected error during attribute access will be caught and logged; the function will return ``False`` in such cases.

    .. note::
        This function is compatible with Django and Django REST Framework request objects. It also supports ASGIRequest and can be used in unit tests with mock objects that have the required attributes.

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
    # pylint: disable=import-outside-toplevel
    from django.core.handlers.asgi import ASGIRequest
    from django.http import HttpRequest
    from rest_framework.request import Request

    from smarter.lib.cache import cache_results

    smarter_process_id = getattr(request, "smarter_process_id", None)
    logger.debug("%s.is_authenticated_request() smarter_process_id: %s", logger_prefix, smarter_process_id or "Not set")
    if not smarter_process_id:
        smarter_process_id = str(random.randint(100000, 999999))

    @cache_results(cache_key=smarter_process_id)
    def cached_is_authenticated_request() -> bool:
        try:
            if not isinstance(request, (HttpRequest, Request, ASGIRequest)):
                logger.warning(
                    "%s.is_authenticated_request() - Invalid request type: %s, expected HttpRequest, Request, or ASGIRequest",
                    logger_prefix,
                    type(request),
                )
                return False

            is_valid_request_object = isinstance(request, (HttpRequest, Request, ASGIRequest))
            if not is_valid_request_object:
                # suggests buggy code, hence the warning
                logger.warning(
                    "%s.is_authenticated_request() Invalid request object of type %s - returning False",
                    logger_prefix,
                    type(request),
                )
                return False

            has_user = hasattr(request, "user")
            if not has_user:
                logger.debug(
                    "%s.is_authenticated_request() Request does not have 'user' attribute - returning False",
                    logger_prefix,
                )
                return False

            has_is_authenticated = has_user and hasattr(request.user, "is_authenticated")
            if not has_is_authenticated:
                # this should not happen in normal code, hence the warning
                logger.warning(
                    "%s.is_authenticated_request() Request.user of type %s does not have 'is_authenticated' attribute - returning False",
                    logger_prefix,
                    type(request.user),
                )
                return False

            url = smarter_build_absolute_uri(request)
            if is_valid_request_object and has_user and has_is_authenticated:
                retval = request.user.is_authenticated
                if retval:
                    return True
            else:
                logger.debug(
                    "%s.is_authenticated_request() Request is not authenticated - returning False URL: %s",
                    logger_prefix,
                    url,
                )
                return False
            if hasattr(request, SMARTER_IS_INTERNAL_API_REQUEST):
                logger.debug(
                    "%s.is_authenticated_request() Request has SMARTER_IS_INTERNAL_API_REQUEST=%s",
                    logger_prefix,
                    getattr(request, SMARTER_IS_INTERNAL_API_REQUEST, False),
                )

            # check request head for Authorization
            if hasattr(request, "headers") and request.headers is not None:
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    logger.debug(
                        "%s.is_authenticated_request() Request has Authorization header (first 4 chars): %s",
                        logger_prefix,
                        str(auth_header)[:4],
                    )
                else:
                    logger.debug(
                        "%s.is_authenticated_request() Request does not have Authorization header",
                        logger_prefix,
                    )
                return retval
            return False

        # pylint: disable=W0718
        except Exception as e:
            logger.error("%s.is_authenticated_request() failed: %s", logger_prefix, logging.formatted_text(str(e)))
            return False

    return cached_is_authenticated_request()


__all__ = ["is_authenticated_request"]
