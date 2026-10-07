"""Signals for orchestrator app.

These signals are used to notify various events in the orchestrator lifecycle,
such as deployment, DNS verification, and API management.
"""

from django.dispatch import Signal

orchestrator_called = Signal()
"""
Signal triggered when a orchestrator is called.

Arguments:
    orchestrator (Orchestrator): The orchestrator instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    orchestrator_called.send(sender=self.__class__, orchestrator=self.orchestrator, request=request, args=args, kwargs=kwargs)
"""
