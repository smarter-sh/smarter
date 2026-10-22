Liveness Probe
==============

The web server answers the Kubernetes liveness and startup probes, ``/healthz/``, in its ASGI
application, before Django and its middleware, so that a busy pod, or one whose Redis or database
stalls, is not restarted. The readiness probe, ``/readiness/``, still goes through Django.

.. automodule:: smarter.lib.django.healthz
    :members:
    :undoc-members:
    :show-inheritance:
