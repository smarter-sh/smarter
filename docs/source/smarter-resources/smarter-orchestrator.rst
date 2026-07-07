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
   orchestrator/serializers
   orchestrator/signals
   orchestrator/tasks
   orchestrator/views
