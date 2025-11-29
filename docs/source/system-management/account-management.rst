Account Management
==================

Unlike traditional Django applications, Smarter adds an Account model that reside **above**
the User model. Each Account can have multiple Users associated with it. Hence, with Smarter,
the true *unique combination* for authentication is the pair of (Account, User), rather than just User alone.
This relationship is implemented as a UserProfile model that links Users to Accounts.

Smarter Accounts are typically used for group / team management, internal billing, and permissioning.
For the avoidance of doubt, this means that cost accounting is done at the Account level, not the User level.
Though in many cases, audit and forensics may be done at the User level using custom Sql queries.

Creating Accounts
-----------------

Use the manage.py command to create new Accounts:

.. code-block:: bash

   python manage.py create_account --company_name "My Organization" --account-number "####-####-####"

.. note::

  Users do not have access to Smarter resources across accounts. Each Account is a Chinese wall.
