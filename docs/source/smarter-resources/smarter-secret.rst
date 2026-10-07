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

Platform administrators can also read and change a Secret's value from the command line, inside
the Smarter application container. ``manage.py get_secret`` decrypts and prints the value of a
Secret that a user may read, and ``manage.py update_secret`` encrypts and saves a new value for a
Secret that the user owns, prompting for the value if ``--value`` is not given:

.. code-block:: console

   python manage.py get_secret --name openai_api_key --username admin
   python manage.py update_secret --name openai_api_key --username admin



Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   secret/api
   secret/admin
   secret/caching
   secret/const
   secret/management
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
