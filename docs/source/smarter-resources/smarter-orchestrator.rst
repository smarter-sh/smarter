Smarter Orchestrator
=====================

Overview
--------

The Smarter Orchestrator app provides a standardized interface for coordinating
multiple LLMClients (Harnesses) toward a shared agentic objective. Rather than
hard-coding the control flow for each multi-model workflow, the Orchestrator
lets an Account administrator declare which LLMClients participate, what role
each one plays, and which coordination strategy governs their interaction —
sequential hand-offs, parallel fan-out, a supervisor delegating to workers, a
router dispatching by intent, or a voting/debate pattern for consensus. This
allows prompts and engineering loops to treat a multi-agent workflow as a
single managed resource, while Smarter remains responsible for sequencing,
authorization, auditing, and execution management. By separating orchestration
logic from the individual LLMClients it coordinates, the Orchestrator enables
new agentic patterns to be composed or reconfigured without modifying the
LLMClients themselves.

The Orchestrator operates as a coordination layer between Smarter and the
LLMClients (Harnesses) attached to it. Each Harness's participation is tracked
independently of the LLMClient itself — its role, execution order, active
status, and any per-membership configuration overrides — so the same LLMClient
can serve different purposes across different Orchestrators. When an
Orchestrator is invoked against a concrete objective, that attempt is recorded
as an OrchestrationRun, with each individual LLMClient invocation captured as
an OrchestrationStep referencing the underlying LLMClient execution record.
This gives administrators a complete, ordered trace of how a run arrived at
its result — or where it failed — without duplicating data already tracked
by the LLMClient layer. Every invocation is executed through Smarter's
existing security, logging, charging, and orchestrator infrastructure, ensuring
that orchestrated workflows remain subject to the same governance and
operational controls as any single-model interaction.

The Smarter Orchestrator app is included in v0.X.Y and later. It enables
Account administrators to configure and manage Orchestrators — their
coordination strategy, member Harnesses, and iteration limits — through the
Smarter administration interface or a declarative Smarter API Manifest (SAM),
eliminating the need to hand-write orchestration logic or distribute
multi-agent control flow across individual applications.

Harnesses in other accounts
---------------------------

A harness names its LLMClient by ``llmClientName``. Without an ``accountNumber``, Smarter uses the nearest LLMClient
of that name in the Orchestrator owner's account tree: the owner's own, else their account's, else that of an
account that shares with theirs. With ``accountNumber``, it uses that account's LLMClient, which the owner must be
able to read, e.g. as a member of the account. So an organization's executives can combine the assistants of their
departments, each of which stays in its department's account:

.. code-block:: yaml

    spec:
      config:
        strategy: parallel
        harnesses:
          - llmClientName: stackademy_hr_assistant
            accountNumber: "2718-2818-0002"
          - llmClientName: stackademy_accounting_assistant
            accountNumber: "2718-2818-0003"
          - llmClientName: stackademy_board_pack
            role: summarizer
            config:
              instructions: Write the board pack's one page from these answers.

Running an Orchestrator
-----------------------

A run is an attempt at an objective. ``POST /api/v1/orchestrators/<id>/runs/`` with ``{"objective": "..."}`` starts
one, and answers ``202`` with the run, ``pending``. The platform executes it in the background, so poll
``GET /api/v1/orchestrators/<id>/runs/<run_id>/`` until its status is ``succeeded``, ``failed`` or
``max_iterations_exceeded``. The run lists its steps, and, once it succeeded, its ``result``.

- **Strategies.** ``sequential`` calls every active harness but the summarizer, in ``executionOrder``, and gives each
  the objective and every answer before it. ``parallel`` gives each only the objective. In ``router``, a harness
  with the role ``router`` reads the objective and the other harnesses' names and descriptions, and chooses the
  one that answers. In ``supervisor``, a harness with the role ``planner`` asks the others questions, one at a time,
  and reads each answer, until it gives the result. Router and planner reply in JSON, which Smarter asks them for,
  so give their LLMClients no tools of their own, or they may answer the objective themselves. After any strategy,
  a ``summarizer`` harness, if there is one, answers last, from every answer. A harness's ``config.instructions``
  ends the messages that it receives. ``voting`` and ``debate`` can't run yet, and their runs are refused.
- **Each step is a prompt** of its LLMClient, as its owner, in its session for the run, one per harness, so that a
  harness asked twice remembers the first time: its tools, guardrails and
  budgets apply, and its tokens are charged to it. A department's assistant reads its department's records, and its
  department pays for it. The user who started the run is each step's acting user, whom MCP servers learn of.
- **Who may run it.** Any user who may read the Orchestrator, and every one of its harness LLMClients. A user who
  may not read one of them is refused with ``403``, so an Orchestrator is never a way into an account that the user
  doesn't belong to. Only the user who started a run, or a superuser, may read it.
- **Limits.** ``maxIterations`` bounds the steps of a run. A budget that has run out fails the step that it would
  charge. A failed step ends a ``sequential`` run; in a ``parallel`` run, the summarizer is told which harness
  failed.
- **Signals.** A run sends a Django signal when it is queued, when a worker starts it, after each step, and when it
  finishes: ``orchestration_run_queued``, ``orchestration_run_started``, ``orchestration_step_finished`` and
  ``orchestration_run_finished`` (see :doc:`orchestrator/signals`). Code that must react to a run, e.g. to notify the
  user who started it, receives them instead of polling the run's status.

:doc:`ADR-037 <../adr/037-orchestration-runtime>` records the design.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   orchestrator/api
   orchestrator/const
   orchestrator/management
   orchestrator/manifest
   orchestrator/models
   orchestrator/runtime
   orchestrator/serializers
   orchestrator/signals
   orchestrator/tasks
   orchestrator/views
