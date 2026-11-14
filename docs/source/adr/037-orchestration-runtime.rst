ADR-037: Orchestration Runtime
==============================

Status
------
Proposed

Context
-------
The Orchestrator kind (``smarter.apps.orchestrator``) declares a multi-agent workflow: a strategy (sequential,
parallel, supervisor, router, voting or debate), a bound on iterations, and harnesses, each an LLMClient with a
role (planner, executor, critic, router, summarizer or tool caller) and an execution order. Its manifest applies,
and its models record what a workflow did: an ``OrchestrationRun`` per attempt at an objective, and an
``OrchestrationStep`` per LLMClient call, which points at that call's ``Prompt``.

Nothing runs one. The prompt endpoint of ``smarter.apps.orchestrator.api.v1.views`` checks the Orchestrator and its
budget, then answers ``GET`` with 405 and has no ``POST`` that executes a strategy, and no code creates a run or a
step. And a harness can name only an LLMClient of the Orchestrator's own account
(``SAMOrchestratorBroker.apply()`` looks it up with ``user_profile__account=self.account``).

Stackademy, the demonstration in https://github.com/smarter-sh/stackademy, shows why both matter. Its executives
want a board pack drawn from four departments' assistants, each of which lives in its department's own account
(ADR-036), reads its department's records through its department's own database user, and is charged to its
department's budget. Today the board pack is one assistant over views of totals, which can't use what the
departments' assistants know.

Decision
--------
Smarter runs Orchestrators, one step at a time, by calling each harness LLMClient exactly as its prompt api does.

1. **A run is asynchronous.** ``POST /api/v1/orchestrators/<hashed_id>/runs/`` with an objective creates an
   ``OrchestrationRun`` (``pending``) and answers ``202`` with its id. A Celery task, on the default queue,
   executes it. ``GET .../runs/<id>/`` returns its status, its steps and its result. A run of several LLM calls
   with tools takes minutes, longer than an http request may wait.

2. **A step is a prompt.** Each step calls the harness LLMClient through the same handler as the LLMClient prompt
   api (``smarter_compatible_client.get_smarter_harness()``, with ``LLMClientPlugin().plugins()``), in a
   ``Prompt`` session of its own, one per harness per run, so that a harness that speaks twice keeps its
   conversation. The step records that ``Prompt``. Everything a prompt already does applies unchanged: tools,
   MCP servers, extensions, guardrails, the journal, the charges and the budgets of the LLMClient and its plugins.

3. **A step runs as its LLMClient's owner**, as the prompt api runs a prompt: HR's assistant uses HR's connection
   and is charged to HR. The person who started the run is the acting user, as for a prompt
   (``smarter.apps.mcpserver.services.acting_user``), so MCP servers learn who asked.

4. **The runner may use every harness.** A run starts only if the user who starts it may read the Orchestrator
   and every active harness LLMClient (``with_read_permission_for``). Otherwise it is refused with 403, before
   any LLM is called. An Orchestrator must not become a way around an account's sharing: Stackademy's CFO, who
   isn't a member of HR, may not reach HR's assistant through the Board Pack. The run records who started it.

5. **A harness may name another account's LLMClient.** ``spec.config.harnesses[].accountNumber`` is optional.
   Without it, the LLMClient is resolved by name in the Orchestrator owner's account tree, nearest first
   (``smarter.apps.account.hierarchy.resolve_by_name``, ADR-036). With it, the LLMClient is looked up by name in
   that account, and applying the manifest requires that the Orchestrator's owner may read it. So the
   executives' Board Pack in Stackademy Corp names each department's assistant in its own account, and each
   executive who runs it must be a member of every department it draws on.

6. **Messages between steps are built in code.** A step receives one user message: the run's objective, the
   outputs of the steps it depends on, labeled by harness, and the harness's own ``config.instructions``, if
   any. Outputs are text, as the harness's assistant wrote them. A run's ``result`` is the last step's output,
   or the summarizer's.

7. **Strategies arrive in phases.** The first version runs:

   - ``sequential``: every active harness but the summarizer, in ``executionOrder``, each given the outputs
     before it;
   - ``parallel``: the same harnesses, each given only the objective;
   - and, in both, a ``summarizer`` harness, if there is one, last, given every output.

   A run of any other strategy is refused with a message that names it, and the manifest still applies.
   ``supervisor`` and ``router``, whose planner or router chooses the next step, come next, and ``voting`` and
   ``debate`` after them, each with its own ADR amendment.

8. **Limits and failure.** ``maxIterations`` bounds the steps of a run. Before each step,
   ``charge_authorization()`` checks the Orchestrator, the harness LLMClient and the runner's profile, so a
   budget that has run out stops the run at the next step. A step that fails fails a ``sequential`` run; in a
   ``parallel`` run it is recorded, and the summarizer is told which harness failed. A run that fails keeps its
   completed steps.

9. **Contracts.** The run's request and response are Pydantic models (ADR-031), in the api's OpenAPI document.
   Only the user who started a run, or a superuser, may read it, since its result holds what that user may read
   in other accounts. A step's own record is its ``Prompt`` session: its messages, tool calls and charges.

Alternatives Considered
-----------------------
- **A synchronous prompt endpoint**, which answers when the run ends. Simple for a client, but a run with several
  tool-using steps outlasts the request timeouts of the load balancer and the web server.
- **A framework** such as LangGraph or CrewAI. Each brings its own model of agents, tools, memory and state,
  beside Smarter's LLMClients, plugins, budgets and journal, which a run must use to stay governed. The control
  flow that Smarter needs is small.
- **Run every step as the runner.** Then HR's assistant would read HR's records with the runner's rights, which
  the runner doesn't have unless they belong to HR, and the charges would land in the runner's account instead
  of the department whose assistant did the work.
- **A budget for the Orchestrator as a whole.** A charge names one resource, the LLMClient or plugin that
  incurred it, so an Orchestrator's budget would need each charge to name two resources, or its own copy of
  each charge, which account totals would count twice. Each step is charged to the harness that did it, and an
  Orchestrator's lock, set by hand or by a later budget kind, still stops its runs.

Consequences
------------
- **Positive:**

  - An Orchestrator does something. Each step is an ordinary, governed prompt, so nothing about tools, budgets,
    guardrails or the journal needs a second implementation.
  - Organizations can combine assistants across their accounts without loosening any account's sharing.
  - A run's trace, step by step, links to each step's ``Prompt``, and so to its messages, tokens and charges.

- **Negative:**

  - Results arrive later: clients poll a run, and the web console needs a run view.
  - A run's cost is spread over its harnesses' accounts, and no single budget caps a run.
  - Harnesses in other accounts make a run depend on resources that their owners may change or delete; a run
    whose harness is gone fails at its start, with the harness's name.
  - ``accountNumber`` is a new field of the Orchestrator manifest, in smarter-types and the SDKs too.

Related ADRs
------------
- :doc:`ADR-024: Broker Model <024-broker-model>`
- :doc:`ADR-031: Pydantic over JSON <031-pydantic-over-json>`
- :doc:`ADR-033: Don't Repeat Yourself <033-dry>`
- :doc:`ADR-036: Account Hierarchy and Resource Sharing <036-account-hierarchy>`
