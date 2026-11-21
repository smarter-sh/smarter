"""Signals for api app."""

from django.dispatch import Signal

api_request_initiated = Signal()
"""
Sent when an API request is initiated.

:Arguments::

    - sender: The sender of the signal.
    - instance: The instance making the request.
    - request: The HTTP request object.

:Example::

    .. code-block:: python

        api_request_initiated.send(sender=self.__class__, instance=self, request=self.request)
"""

api_request_completed = Signal()
"""
Sent when an API request is completed.

:Arguments::
    - sender: The sender of the signal.
    - instance: The instance making the request.
    - request: The HTTP request object.
    - response: The HTTP response object.

:Example::

    .. code-block:: python

        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
"""
api_request_failed = Signal()
"""
Sent when an API request fails, from inside the view's ``except`` block, before the error response is returned.

:Arguments::
    - sender: The sender of the signal.
    - instance: The instance making the request.
    - request: The HTTP request object.
    - response: The HTTP response object, or None if the view returned none before it failed.
    - exception: The exception that failed the request.
    - status: The http status of the error response, e.g. 403 or 500.
    - description: The error description returned to the client, or None for the exception's own message.
:Example::

    .. code-block:: python

        api_request_failed.send(
            sender=self.__class__,
            instance=self,
            request=request,
            response=response,
            exception=e,
            status=status,
            description=description,
        )
"""
