"""Signals for mcpclient app.

These signals are used to notify various events in the mcpclient lifecycle,
such as deployment, DNS verification, and API management.
"""

from django.dispatch import Signal

mcpclient_called = Signal()
"""
Signal triggered when a mcpclient is called.

Arguments:
    mcpclient (MCPClient): The mcpclient instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    mcpclient_called.send(sender=self.__class__, mcpclient=self.mcpclient, request=request, args=args, kwargs=kwargs)
"""
