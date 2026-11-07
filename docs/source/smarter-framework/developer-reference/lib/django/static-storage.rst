Static Files on the CDN
=======================

While ``SMARTER_STATIC_FILES_ON_CDN`` is on, the platform's static files, the web console's scripts
among them, are stored in the environment's S3 bucket, under ``static/``, and pages load them from
its CDN, ``cdn.<platform>``. ``initialize_platform`` uploads them on each deployment, then records the
console's build, and the console's page switches to the CDN only once its build is recorded. Until
then, and whenever the setting is off, the server serves them itself. See
:doc:`ADR-035 </adr/035-single-page-app>`.

.. automodule:: smarter.lib.django.static_storage
    :members:
    :undoc-members:
    :show-inheritance:
