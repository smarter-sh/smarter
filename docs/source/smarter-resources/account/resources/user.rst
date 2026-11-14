User Resource
==================

A Django User represents an individual user account within the Smarter platform, related to an :doc:`account`.
Users have specific roles and permissions.

.. literalinclude:: ../../../example-manifests/user.yaml
   :language: yaml
   :caption: Example User Manifest

A user belongs to the account of whoever applies their manifest. In an organization of several accounts, such as a
company and its departments (see :doc:`account`), ``spec.accounts`` lists the accounts that the user belongs to
instead, and whether they administer each one:

.. code-block:: yaml

   spec:
     config:
       email: cfo@example.com
       firstName: Avery
       lastName: Example
       isActive: true
     accounts:
       - accountNumber: "2718-2818-0002" # Accounting, which they administer
         isAccountAdmin: true
       - accountNumber: "2718-2818-0003" # HR, as a member
       - accountNumber: "2718-2818-0004" # Content, as a member

Applying the manifest adds each membership that is missing and updates the others. It never removes one, because
removing a user from an account would delete everything that they own there. A superuser may list any account;
an account's administrator may list only the accounts that they administer.

Technical References
--------------------

- Django ORM Model: :py:class:`django.contrib.auth.models.User`
- :doc:`SAM Broker <../sam/brokers/user>`
- :doc:`SAM Pydantic Class Reference <../sam/models/user>`
