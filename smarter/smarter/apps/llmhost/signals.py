"""Signals for llmhost app.

These signals are used to notify various events in the llmhost lifecycle,
such as deployment, DNS verification, and API management.
"""

from django.dispatch import Signal

llmhost_called = Signal()
"""
Signal triggered when a llmhost is called.

Arguments:
    llmhost (LLMHost): The llmhost instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    llmhost_called.send(sender=self.__class__, llmhost=self.llmhost, request=request, args=args, kwargs=kwargs)
"""
