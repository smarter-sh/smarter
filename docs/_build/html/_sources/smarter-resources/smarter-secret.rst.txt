Smarter Secret
================

Overview
--------

Smarter Secret is a standard credentials vault, seamlessly integrated with every
other Smarter resource that relies on sensitive information for authentication
and connectivity. Secrets can be shared across teams and referenced by dependent
resources without ever exposing the underlying value, and, like any other Smarter
resource, a Secret is defined and managed through a standard SAM manifest.

* :doc:`Smarter Secret <secret/resources/secret>`: a Django ORM-based secure store
* for sensitive information such as SQL connection strings and API keys. Secrets
* are consumed by other Smarter resources to supply the authentication credentials
* those resources need to reach remote services.

.. literalinclude:: ../example-manifests/secret.yaml
   :language: yaml
   :caption: Example Smarter Secret Manifest



Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   secret/api
   secret/admin
   secret/caching
   secret/const
   secret/manifest
   secret/models
   secret/receivers
   secret/resources
   secret/serializers
   secret/signals
   secret/templatetags
   secret/tasks
   secret/urls
   secret/views
