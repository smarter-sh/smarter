Smarter Secret
================

Overview
--------

The Smarter Secret module provides secure storage capabilities for the Smarter platform,
with seamless integration to Smarter resources that rely on sensitive information
for authentication and connectivity.

- :doc:`Smarter Secret <secret/secret>`: A Django ORM-based secure storage for sensitive
    information like SQL connection strings and API keys. Secrets are used by other
    Smarter resources to provide authentication credentials for remote services.

Usage
-----

.. seealso::

  - :doc:`Example Manifests <secret/data/example-manifests/secret-smarter-test-db.yaml>`: An example manifest for creating a Smarter Secret using SAM.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   secret/api
   secret/const
   secret/manifests
   secret/models
   secret/receivers
   secret/sam
   secret/serializers
   secret/signals
   secret/tasks
   secret/views
