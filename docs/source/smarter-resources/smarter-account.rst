Smarter Account
================

Overview
--------

The Smarter Account module provides multi-tenant account management capabilities for the Smarter platform.
It enables organizations to create and manage accounts, users, and secure storage of sensitive information.

- :doc:`Smarter Account <account/account>`: An organizational unit for grouping users and resources. An account can represent
    a company, department, team, or project.
- :doc:`Smarter User <account/user>`: A Django user that belongs to a Smarter Account.
- :doc:`Smarter Secret <account/secret>`: A Django ORM-based secure storage for sensitive information like SQL connection strings and API keys.
    Secrets are used by other Smarter resources to provide authentication credentials for remote services.

Usage
-----

.. note::

  Usage of Smarter Account and User resources is implied as part of your interaction with other Smarter resources.
  When you create a Smarter resource, it is automatically associated with your current Smarter Account and User.

.. seealso::

  - :doc:`Example Manifests <account/sam/example-manifests>`: An example manifest for creating a Smarter Secret using SAM.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   account/account
   account/user
   account/secret
   account/api
   account/models
   account/sam
   account/serializers
   account/signals
   account/tasks
   account/utils
