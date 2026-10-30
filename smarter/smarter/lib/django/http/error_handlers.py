"""
The error pages of every Smarter urlconf: Django's own views, which close their database connections.

Under ASGI, Django renders the response to an exception raised by a view or a middleware, e.g.
``Http404``, ``PermissionDenied`` or ``SuspiciousOperation``, with
``sync_to_async(response_for_exception, thread_sensitive=False)``, in a thread of the event
loop's default executor, outside the request cycle. With ``DEBUG`` off, the page renders a
template whose context processors query the database, so it opens a connection in that thread,
which nothing closes. Chat prompts run in the same executor
(:func:`smarter.apps.prompt.progress.prompt_event_stream`), so the first prompt to land in the
thread hours later reused the idle connection, which MariaDB had closed after its
``wait_timeout``, and failed with ``(2006, "MySQL server has gone away")``. Bots requesting
``/favicon.ico``, ``/robots.txt`` or ``/.env`` left one such connection in every app process.

Each view here is Django's default view, from :mod:`django.views.defaults`, followed by
:func:`smarter.lib.django.connections.close_thread_connections`. Every urlconf that a host
routes to (:mod:`smarter.urls.console`, :mod:`smarter.urls.api` and
:mod:`smarter.urls.llmclients`) names them as its ``handler400``, ``handler403``, ``handler404``
and ``handler500``.
"""

from collections.abc import Callable
from functools import wraps

from django.http import HttpResponse
from django.views import defaults

from smarter.lib.django.connections import close_thread_connections


def closing_connections(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """
    Wrap an error view so that it closes its thread's database connections when it returns.

    The view's response is rendered by the time it returns, so nothing it does needs the
    connection afterwards. :func:`functools.wraps` keeps the view's signature, which Django's
    system check of custom error handlers reads.

    :param view: An error view, e.g. :func:`django.views.defaults.page_not_found`.
    :type view: Callable[..., HttpResponse]
    :returns: The view, closing the current thread's connections after it runs.
    :rtype: Callable[..., HttpResponse]
    """

    @wraps(view)
    def wrapper(*args, **kwargs) -> HttpResponse:
        try:
            return view(*args, **kwargs)
        finally:
            close_thread_connections()

    return wrapper


bad_request = closing_connections(defaults.bad_request)
"""``handler400``: Django's 400 page, :func:`django.views.defaults.bad_request`."""

permission_denied = closing_connections(defaults.permission_denied)
"""``handler403``: Django's 403 page, :func:`django.views.defaults.permission_denied`."""

page_not_found = closing_connections(defaults.page_not_found)
"""``handler404``: Django's 404 page, :func:`django.views.defaults.page_not_found`."""

server_error = closing_connections(defaults.server_error)
"""``handler500``: Django's 500 page, :func:`django.views.defaults.server_error`."""

__all__ = [
    "bad_request",
    "closing_connections",
    "page_not_found",
    "permission_denied",
    "server_error",
]
