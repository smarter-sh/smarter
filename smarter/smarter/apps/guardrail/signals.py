"""Signals for guardrail app.

These signals are used to notify various events in the guardrail lifecycle,
such as deployment, DNS verification, and API management.
"""

from django.dispatch import Signal

guardrail_called = Signal()
"""
Signal triggered when a guardrail is called.

Arguments:
    guardrail (Guardrail): The guardrail instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    guardrail_called.send(sender=self.__class__, guardrail=self.guardrail, request=request, args=args, kwargs=kwargs)
"""
