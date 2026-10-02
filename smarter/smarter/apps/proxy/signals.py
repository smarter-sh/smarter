"""Signals for proxy app."""

from django.dispatch import Signal

broker_ready = Signal()
"""Sent when a Proxy broker is ready.

Arguments: ``broker``.
"""

proxy_request_completed = Signal()
"""
Sent when the provider has responded to a request that a Proxy forwarded, whatever its status.

For a stream, it is sent when the stream ends. Arguments: ``proxy``, ``user_profile``, ``method``,
``path``, ``status``, ``usage`` (a :class:`~smarter.apps.proxy.services.Usage`, or ``None``) and
``elapsed`` (seconds).
"""

proxy_request_failed = Signal()
"""
Sent when a Proxy refuses a request, or cannot reach the provider.

Arguments: ``proxy``, ``user_profile``, ``method``, ``path``, ``error`` (a
:class:`~smarter.apps.proxy.exceptions.ProxyError`) and ``elapsed`` (seconds).
"""
