"""
Module: smarter.common.utils.smarter_build_absolute_uri
"""

import logging
from typing import Optional

from django.http import HttpRequest

from smarter.common.helpers.console_helpers import formatted_text, formatted_text_red
from smarter.lib.django.validators import SmarterValidator

logger = logging.getLogger(__name__)

logger_prefix = formatted_text(f"{__name__}.smarter_build_absolute_uri()")


def smarter_build_absolute_uri(request: "HttpRequest") -> Optional[str]:
    """
    Attempts to construct the absolute URI for a given request object.

    :param request: The request object, which may be an instance of :class:`django.http.HttpRequest`, :class:`rest_framework.request.Request`, :class:`django.core.handlers.wsgi.WSGIRequest`, or a mock object for testing.
    :type request: "HttpRequest" or compatible type

    :return: The absolute URI as a string, or a fallback test URL if the request is invalid or cannot be resolved.
    :rtype: Optional[str]

    .. note::
        - If the request is a Django REST Framework ``Request``, it is recast to a Django ``HttpRequest``.
        - If the request is a mock object (e.g., from unit tests), a synthetic test URL is returned.
        - The function first tries to use Django's ``build_absolute_uri`` method. If unavailable, it attempts to build the URL from scheme, host, and path attributes.
        - If all attempts fail, a generic fallback URL is returned.

    .. warning::
        If the request is ``None`` or cannot be resolved, the function logs a warning and returns a fallback test URL. Always validate the returned URL before using it in production.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import smarter_build_absolute_uri
        from django.http import HttpRequest

        request = HttpRequest()
        request.META['HTTP_HOST'] = 'localhost:9357'
        request.path = '/api/v1/resource/'
        url = smarter_build_absolute_uri(request)
        print(url)  # Output: http://localhost:9357/api/v1/resource/

        # Example with DRF Request
        from rest_framework.request import Request
        drf_request = Request(...)
        url = smarter_build_absolute_uri(drf_request)
        print(url)

        # Example with None
        url = smarter_build_absolute_uri(None)
        print(url)  # Output: http://testserver/unknown/

    """

    def get_host(request: "HttpRequest") -> str:
        """
        Helper function to extract the host from the request object.
        """
        try:
            # Try Django's get_host method first. works well except that
            # it can raise KeyError on certain edge cases.
            if hasattr(request, "get_host"):
                retval = request.get_host()
                logger.debug(
                    "%s.smarter_build_absolute_uri() obtained host from %s request.get_host(): %s",
                    logger_prefix,
                    type(request).__name__,
                    retval,
                )
                return retval
        except KeyError:
            pass
        if hasattr(request, "META") and "HTTP_HOST" in request.META:
            retval = request.META["HTTP_HOST"]
            logger.debug(
                "%s.smarter_build_absolute_uri() obtained host from %s request.META['HTTP_HOST']: %s",
                logger_prefix,
                type(request).__name__,
                retval,
            )
            return retval
        if hasattr(request, "META") and "SERVER_NAME" in request.META:
            retval = request.META["SERVER_NAME"]
            logger.debug(
                "%s.smarter_build_absolute_uri() obtained host from %s request.META['SERVER_NAME']: %s",
                logger_prefix,
                type(request).__name__,
                retval,
            )
            return retval
        logger.warning(
            "%s.smarter_build_absolute_uri() could not determine host from %s request; returning 'testserver'",
            logger_prefix,
            type(request).__name__,
        )
        return "testserver"

    if request is None:
        retval = "http://testserver/unknown/"
        logger.warning(
            "%s.smarter_build_absolute_uri() called with None request. Returning fallback URL: %s",
            logger_prefix,
            retval,
        )
        return retval

    # If it's a unittest.mock.Mock, synthesize a fake URL for testing
    if hasattr(request, "__class__") and request.__class__.__name__ == "Mock":
        retval = "http://testserver/mockpath/"
        logger.debug(
            "%s.smarter_build_absolute_uri() called with Mock request; returning fake test URL: %s",
            logger_prefix,
            retval,
        )
        return retval

    # Try to use Django's build_absolute_uri if available
    if hasattr(request, "build_absolute_uri") and getattr(request, "META", {}).get("SERVER_NAME") is not None:
        try:
            url = request.build_absolute_uri()
            if url:
                return url
        # pylint: disable=W0718
        except Exception as e:
            logger.warning(
                "%s.smarter_build_absolute_uri() failed to call request.build_absolute_uri(): %s",
                logger_prefix,
                formatted_text_red(str(e)),
            )

    # Try to build from scheme, host, and path
    try:
        scheme = getattr(request, "scheme", None) or getattr(request, "META", {}).get("wsgi.url_scheme", "http")
        host = get_host(request)
        path = getattr(request, "get_full_path", lambda: None)() or "/"
        url = f"{scheme}://{host}{path}"
        if SmarterValidator.is_valid_url(url):
            logger.debug("%s.smarter_build_absolute_uri() built URL from request attributes: %s", logger_prefix, url)
            return url
    except KeyError as e:
        logger.debug(
            "%s.smarter_build_absolute_uri() could not build url from request attributes due to a KeyError: %s",
            logger_prefix,
            formatted_text_red(str(e)),
        )
    # pylint: disable=W0718
    except Exception as e:
        logger.debug(
            "%s.smarter_build_absolute_uri() failed to build URL from request attributes: %s (%s)",
            logger_prefix,
            formatted_text_red(str(e)),
            type(e),
        )

    # do this last since we have to import
    # pylint: disable=import-outside-toplevel
    from rest_framework.request import Request

    if isinstance(request, Request):
        # recast DRF Request to Django HttpRequest
        # pylint: disable=W0212
        if hasattr(request, "_request"):
            logger.debug(
                "%s.smarter_build_absolute_uri() recasting DRF Request to Django HttpRequest",
                logger_prefix,
            )
            request = request._request  # type: ignore
        if hasattr(request, "build_absolute_uri"):
            logger.debug(
                "%s.smarter_build_absolute_uri() obtaining URL from recast DRF request.build_absolute_uri()",
                logger_prefix,
            )
            return request.build_absolute_uri()

    # Fallback: synthesize a generic test URL
    logger.debug("%s.smarter_build_absolute_uri() could not determine URL, returning fallback test URL", logger_prefix)
    return "http://testserver/unknown/"


__all__ = ["smarter_build_absolute_uri"]
