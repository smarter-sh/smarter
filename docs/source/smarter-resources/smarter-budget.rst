Smarter Budget
=====================

Overview
--------

A Smarter Budget is a set of spending limits, in USD or in tokens, per hour, day, week or month,
and in total. It is enforced on each of the resources that it is attached to: a user, an
:doc:`Account <smarter-account>`, an :doc:`LLMClient <smarter-llmclient>`, a
:doc:`Provider <smarter-provider>`, a :doc:`Proxy <smarter-proxy>`, an
:doc:`LLMHost <smarter-llmhost>` compute, a :doc:`Plugin <smarter-plugin>`, a
:doc:`Connection <smarter-connection>`, an :doc:`MCPClient <smarter-mcpclient>`, and more.

When a resource's spending reaches a limit, Smarter refuses further requests that would be
charged to it, until the billing period renews or the budget is raised. An LLMClient's chat
answers with the budget's message instead of calling the LLM, and the Proxy and APIs answer
``402 Payment Required``. A budget can optionally also only warn, sending a signal instead
of refusing.

Budgets are managed by superusers, with Budget manifests. ``spec.resources`` lists the resources
that the budget is enforced on, by kind and name:

.. literalinclude:: ../../../smarter/smarter/apps/account/data/example-manifests/budgets/student-monthly-allowance.yaml
   :language: yaml
   :caption: Example Budget Manifest

The web console's **Budgets** page, and the dashboard's **Budget vs Actual** chart, show each
resource's spending against its budget.

.. note::

   Budgets are included in v0.16.0 and later. ``manage.py initialize_platform`` creates a
   catalogue of built-in budgets, detached, which superusers can attach to resources.

.. seealso::

   - :doc:`Cost Accounting <../smarter-platform/cost-accounting>`: pricing, and how budgets are enforced.
   - :doc:`Budget example manifests <account/sam/example-manifests/budget>`

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   account/models/budget
   account/sam/brokers/budget
   account/sam/models/budget
   account/commands/add_builtin_budgets
