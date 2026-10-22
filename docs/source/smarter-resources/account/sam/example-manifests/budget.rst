Budget Example Manifests
==================================

These examples are in the `budgets/ <https://github.com/smarter-sh/example-manifests/tree/main/budgets>`__
folder of the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`, except for the Stackademy project budget, which is in the
`smarter-sh/stackademy <https://github.com/smarter-sh/stackademy>`__ repository with the rest of the
:doc:`Stackademy example project </smarter-framework/smarter-manifests/stackademy>`. Apply one with
``smarter apply -f <file>``. Only superusers may apply a Budget.

Each example is detached: its ``spec.resources`` is empty, ``resources: []``, and the resources
that it could be attached to are shown above it as a commented-out example. Uncomment them, or
list your own, to attach it. ``manage.py initialize_platform`` creates a built-in budget from each
of the examples, with ``manage.py load_from_github``, so they enforce nothing until a superuser
attaches them. A detached budget is created once: one that already exists is left as it is, so a
superuser's attachments and changes survive the next initialization. The Stackademy project budget is different: ``initialize_platform``
applies it, as the Smarter admin, with the rest of the Stackademy repository, so it is attached to
the Smarter account's ``stackademy_sql`` LLMClient and SqlPlugin.

Overview
--------

.. literalinclude:: ../../../../example-manifests/budget.yaml
   :language: yaml
   :linenos:

Per-user monthly allowance
--------------------------

.. literalinclude:: /_example-manifests/budgets/student-monthly-allowance.yaml
   :language: yaml
   :linenos:

From `budgets/student-monthly-allowance.yaml <https://github.com/smarter-sh/example-manifests/blob/main/budgets/student-monthly-allowance.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

Per-user hourly token throttle
------------------------------

.. literalinclude:: /_example-manifests/budgets/user-hourly-token-throttle.yaml
   :language: yaml
   :linenos:

From `budgets/user-hourly-token-throttle.yaml <https://github.com/smarter-sh/example-manifests/blob/main/budgets/user-hourly-token-throttle.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

Organizational monthly cost constraint
--------------------------------------

.. literalinclude:: /_example-manifests/budgets/account-monthly-cap.yaml
   :language: yaml
   :linenos:

From `budgets/account-monthly-cap.yaml <https://github.com/smarter-sh/example-manifests/blob/main/budgets/account-monthly-cap.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

Project budget
--------------

.. code-block:: yaml
   :linenos:

   apiVersion: smarter.sh/v1
   kind: Budget
   metadata:
     name: stackademy_project
     description: |
       An example Budget manifest: a project budget. The Stackademy LLMClient and its SQL plugin may
       spend $10,000 over the six months of the project, and no more than $2,500 in any one month.
       After six months the budget no longer applies.
     version: 1.0.0
     tags:
       - example
       - project
     annotations:
       - smarter.sh/budget/purpose: project budget
   spec:
     config:
       unit: cost
       period: month
       periodicLimit: 2500.00
       absoluteLimit: 10000.00
       duration: 6
       action: block
       warningThreshold: 80
       message: The Stackademy project has used its budget. Please contact the project owner.
     resources:
       - kind: LLMClient
         name: stackademy_sql
       - kind: SqlPlugin
         name: stackademy_sql

From `budgets/stackademy-project.yaml <https://github.com/smarter-sh/stackademy/blob/main/budgets/stackademy-project.yaml>`__ in the :doc:`Stackademy example project </smarter-framework/smarter-manifests/stackademy>`.

Provider daily budget
---------------------

.. literalinclude:: /_example-manifests/budgets/provider-daily.yaml
   :language: yaml
   :linenos:

From `budgets/provider-daily.yaml <https://github.com/smarter-sh/example-manifests/blob/main/budgets/provider-daily.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

LLMHost compute budget
----------------------

.. literalinclude:: /_example-manifests/budgets/llmhost-compute.yaml
   :language: yaml
   :linenos:

From `budgets/llmhost-compute.yaml <https://github.com/smarter-sh/example-manifests/blob/main/budgets/llmhost-compute.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

Spending alerts only
--------------------

.. literalinclude:: /_example-manifests/budgets/proxy-warn-only.yaml
   :language: yaml
   :linenos:

From `budgets/proxy-warn-only.yaml <https://github.com/smarter-sh/example-manifests/blob/main/budgets/proxy-warn-only.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.
