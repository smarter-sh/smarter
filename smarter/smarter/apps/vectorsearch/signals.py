"""Signals for vectorsearch app.

These signals are used to notify various events in the vectorsearch lifecycle,
such as deployment, DNS verification, and API management.
"""

from django.dispatch import Signal

vectorsearch_called = Signal()
"""
Signal triggered when a vectorsearch is called.

Arguments:
    vectorsearch (Vectorsearch): The vectorsearch instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    vectorsearch_called.send(sender=self.__class__, vectorsearch=self.vectorsearch, request=request, args=args, kwargs=kwargs)
"""
