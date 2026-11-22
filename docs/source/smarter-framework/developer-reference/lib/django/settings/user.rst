User Settings
=============

The user's own Django settings, which supersede Smarter's in every environment. How to write them, and
where they go (``user-settings/`` or ``DJANGO_*`` variables locally, ``DJANGO_*`` variables in the Helm
chart's ``env`` on Kubernetes), is in
:doc:`/smarter-platform/user-defined-django-settings`.

.. automodule:: smarter.settings.user
   :members:
   :show-inheritance:
