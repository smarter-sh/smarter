Account Resource
================

An organizational unit for grouping users and resources within the Smarter platform.
An Account can represent a team, department, or project, providing a way to manage access and
resources collectively.

.. literalinclude:: ../../example-manifests/account.yaml
   :language: yaml
   :caption: Example Account Manifest

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.account.models.Account`
- :doc:`SAM Broker <sam/brokers/account>`
- :doc:`SAM Pydantic Class Reference <sam/models/account>`
