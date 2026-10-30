Thread Database Connections
===========================

Django closes a thread's database connection at the start and end of each request, in the thread
that handles the request. Work that runs in another thread, e.g. a chat prompt in the event loop's
executor, an extension tool in its own thread, or an error page that Django's ASGI handler renders
outside the request, closes its connections itself when it finishes, so that the next work in the
same thread doesn't reuse a connection that the database server has since closed.

.. automodule:: smarter.lib.django.connections
    :members:
    :undoc-members:
    :show-inheritance:
