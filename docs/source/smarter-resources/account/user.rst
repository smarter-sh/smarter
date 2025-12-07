User Resource
==================

A Django User represents an individual user account within the Smarter platform, related to an :doc:`account`.
Users have specific roles and permissions.

.. literalinclude:: ../../example-manifests/user.yaml
   :language: yaml
   :caption: Example User Manifest

Technical References
--------------------

- Django ORM Model: :py:class:`django.contrib.auth.models.User`
- :doc:`SAM Broker <sam/brokers/user>`
- :doc:`SAM Pydantic Class Reference <sam/models/user>`
