HTTP Shortcuts
==================

.. automodule:: smarter.lib.django.http.shortcuts
    :members:
    :undoc-members:
    :show-inheritance:

Error Pages
-----------

Every urlconf that a host routes to names these views as its ``handler400``, ``handler403``,
``handler404`` and ``handler500``. They are Django's own error pages, which also close the database
connections of the thread that rendered them.

.. automodule:: smarter.lib.django.http.error_handlers
    :members:
    :undoc-members:
    :show-inheritance:
