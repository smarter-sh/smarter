"""Receiver functions for the api app's signals."""

# pylint: disable=W0613

from http import HTTPStatus
from typing import Optional

from django.dispatch import receiver
from rest_framework.request import Request

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .signals import api_request_completed, api_request_failed, api_request_initiated

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])


def user_for_log(request: Request) -> str:
    """
    Identify the request's user for a log entry, by id, never by username.

    ``str(User)`` is the username, which is often a person's name, so the user itself is never logged.

    :param request: The request.
    :returns: ``user_id=<pk>`` for an authenticated user, ``anonymous`` for an anonymous one, and
        ``N/A`` when the request has no user.
    """
    if not hasattr(request, "user"):
        return "N/A"
    user = request.user
    if not hasattr(user, "is_authenticated"):
        return "N/A"
    if not user.is_authenticated:
        return "anonymous"
    user_id = f"user_id={user.pk}"
    return user_id


@receiver(api_request_initiated, dispatch_uid="api_request_initiated")
def handle_api_request_initiated(sender, instance, request: Request, **kwargs):
    """
    Log the start of an API request: the view's class, path, method and user's id.

    :param sender: The signal's sender.
    :param instance: The view that handles the request.
    :param request: The request.
    """
    logger.info(
        "%s - %s - %s - %s",
        instance.__class__.__name__,
        request.path,
        request.method,
        user_for_log(request),
    )


@receiver(api_request_completed, dispatch_uid="api_request_completed")
def handle_api_request_completed(sender, instance, request: Request, response, **kwargs):
    """
    Log the end of an API request: the view's class, path, method and user's id.

    :param sender: The signal's sender.
    :param instance: The view that handled the request.
    :param request: The request.
    :param response: The response, which is not logged.
    """

    logger.info(
        "%s - %s - %s - %s",
        instance.__class__.__name__,
        request.path,
        request.method,
        user_for_log(request),
    )


@receiver(api_request_failed, dispatch_uid="api_request_failed")
def handle_api_request_failed(
    sender,
    instance,
    request: Request,
    response=None,
    exception: Optional[BaseException] = None,
    status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description: Optional[str] = None,
    **kwargs,
):
    """
    Log a failed API request: a 500 at ERROR, with its traceback, and any other status at WARNING.

    A 500 is a bug, so it logs the exception itself. A client error, e.g. a missing api key or an
    invalid manifest, logs the description that the client is told, so that the log says what the
    client did wrong without repeating anything the client didn't already see.

    The sender sends this signal from inside its ``except`` block, so the exception being handled
    is still current, and ``exc_info=True`` logs its traceback.

    :param sender: The signal's sender.
    :param instance: The view that handled the request.
    :param request: The request.
    :param response: The response, if the view returned one before it failed (unused).
    :param exception: The exception that failed the request.
    :param status: The http status of the error response.
    :param description: The error description returned to the client, or None for the exception's own message.
    """
    if status == HTTPStatus.INTERNAL_SERVER_ERROR.value:
        logger.error("%s: %s", type(exception), str(exception), exc_info=True)
        return
    logger.warning("%s %s: %s", status, type(exception), description)
