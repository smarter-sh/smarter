Account
================

An Account represents an organizational unit containing multiple Django users within the Smarter platform.
Every account has one or more denoted "account administrators" who have permissions to manage the account,
including adding and removing users, and configuring account-wide settings.

Smarter resources owned by account administrators are viewable and usable by all users within the account.


.. literalinclude:: ../../../example-manifests/account.yaml
   :language: yaml
   :caption: Example Account Manifest


Organizations and sharing
-------------------------

Accounts form a tree that describes an organization: a company and its departments, a subsidiary and its own
departments. Each account names its ``parent``, the account above it. An account without one is directly under
the Smarter account, the root of the tree, which every platform has.

Separately, each account decides who may read its resources, with ``shareScope``: itself or one of its
ancestors, whose whole subtree may then read them. An account that omits it shares nothing. The Smarter account
shares with every account, so the Providers, Guardrails and examples that it owns are available to everyone.

For example, an IT department that keeps its company's Secrets and Connections in one place shares them with its
company, and every department of that company may use them, while another company on the same platform can't:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Account
   metadata:
     name: stackademy_it
     description: Stackademy's IT department, which runs the shared services of every department.
     version: 1.0.0
     accountNumber: "2718-2818-0001"
   spec:
     config:
       companyName: Stackademy IT
       parent: "2718-2818-0000" # Stackademy Corp
       shareScope: "2718-2818-0000" # every account under Stackademy Corp

Sharing grants permission to read and use a resource, never to change it, and it reaches down the tree only: a
company can't read its departments' resources because it is their parent. A person who works in several
accounts, such as a chief financial officer, has a profile in each.

When a resource names another, such as a SqlPlugin its Connection, Smarter finds the nearest one of that name:
the owner's own, then their account's, then that of the nearest account that shares with theirs. A department
may override a shared resource by giving its own the same name. Only a superuser may apply an Account manifest.

Each account can have its own administrators. A member whose profile in an account is marked
``is_account_admin`` manages every resource in that account, and nothing in the other accounts that they belong
to: the head of a department administers the department, without becoming an administrator of the company. Unlike
a staff user, an account's administrator has no access to the Django admin site, and can't make anyone staff.

The design, and the alternatives that were considered, are in :doc:`ADR-036 <../../../adr/036-account-hierarchy>`.


Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.account.models.Account`
- :doc:`SAM Broker <../sam/brokers/account>`
- :doc:`SAM Pydantic Class Reference <../sam/models/account>`
