Budget Example Manifests
==================================

These examples are in ``smarter/apps/account/data/example-manifests/budgets/``. Apply one with
``smarter apply -f <file>``. Only superusers may apply a Budget.

``manage.py initialize_platform`` creates a built-in budget from each of them, with
``manage.py add_builtin_budgets``. Built-in budgets are created detached: their ``spec.resources``
is ignored, so they enforce nothing until a superuser attaches them. A budget that already
exists is left as it is.

Overview
--------

.. literalinclude:: ../../../../example-manifests/budget.yaml
   :language: yaml
   :linenos:

Per-user monthly allowance
--------------------------

.. literalinclude:: ../../../../../../smarter/smarter/apps/account/data/example-manifests/budgets/student-monthly-allowance.yaml
   :language: yaml
   :linenos:

Per-user hourly token throttle
------------------------------

.. literalinclude:: ../../../../../../smarter/smarter/apps/account/data/example-manifests/budgets/user-hourly-token-throttle.yaml
   :language: yaml
   :linenos:

Organizational monthly cost constraint
--------------------------------------

.. literalinclude:: ../../../../../../smarter/smarter/apps/account/data/example-manifests/budgets/account-monthly-cap.yaml
   :language: yaml
   :linenos:

Project budget
--------------

.. literalinclude:: ../../../../../../smarter/smarter/apps/account/data/example-manifests/budgets/project.yaml
   :language: yaml
   :linenos:

Provider daily budget
---------------------

.. literalinclude:: ../../../../../../smarter/smarter/apps/account/data/example-manifests/budgets/provider-daily.yaml
   :language: yaml
   :linenos:

LLMHost compute budget
----------------------

.. literalinclude:: ../../../../../../smarter/smarter/apps/account/data/example-manifests/budgets/llmhost-compute.yaml
   :language: yaml
   :linenos:

Spending alerts only
--------------------

.. literalinclude:: ../../../../../../smarter/smarter/apps/account/data/example-manifests/budgets/proxy-warn-only.yaml
   :language: yaml
   :linenos:
