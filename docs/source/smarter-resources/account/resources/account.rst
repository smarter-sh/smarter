Account
================

An Account represents an organizational unit containing multiple Django users within the Smarter platform.
Every account has one or more denoted "account administrators" who have permissions to manage the account,
including adding and removing users, and configuring account-wide settings.

Smarter resources owned by account administrators are viewable and usable by all users within the account.


.. literalinclude:: ../../example-manifests/account.yaml
   :language: yaml
   :caption: Example Account Manifest


Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.account.models.Account`
- :doc:`SAM Broker <../sam/brokers/account>`
- :doc:`SAM Pydantic Class Reference <../sam/models/account>`
