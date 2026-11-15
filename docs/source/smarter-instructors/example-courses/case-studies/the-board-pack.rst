The Board Pack: Orchestrating Assistants Across Organizational Boundaries
=========================================================================

*How Stackademy's executives got one quarterly board pack from four departments' assistants, each behind its own
account, without giving the executives, or the orchestration, any access that the departments hadn't granted.*

At a glance
-----------

.. list-table::
   :widths: 25 75

   * - Organization
     - Stackademy's executives: the chief executive and the chief financial officer, in the company's own account.
   * - Challenge
     - The board wants one page a quarter on people, finances, course production and admissions. The knowledge is
       in four departments' assistants, each in an account that the others can't read, and each charged to its own
       budget. Smarter's Orchestrator kind could declare a multi-agent workflow, but nothing ran one.
   * - Solution
     - First, an interim: Atlas, an assistant over five database views of totals. Then an orchestration runtime in
       Smarter, decided in ADR-037: each step is an ordinary prompt of a department's assistant, run as its owner,
       charged to its department; the run is refused unless its runner may use every assistant.
   * - Smarter features
     - Orchestrator (sequential, parallel, router, supervisor, summarizer), LLMClient, SqlPlugin, ``SQL SECURITY
       DEFINER`` views, the runs api, the web console's Runs section
   * - Outcome
     - A quarterly board pack in one request, from the departments' own assistants, whose every step is a governed,
       journaled prompt; the CFO, who isn't a member of HR, is refused, by design.

Executive summary
-----------------

A board pack is the textbook case for a multi-agent system: several specialists, each expert in one part of the
business, and an editor who combines their answers into one document. It is also a textbook case of a system that
can quietly defeat an organization's access controls. An orchestration that calls HR's assistant on behalf of
whoever starts it is, unless it is designed not to be, a way for anyone who may start it to read HR's records.

Stackademy took two steps. The first was quick and safe: **Atlas**, an assistant for the executives over five
database views that return only totals, such as headcount and payroll by department, never a person's salary. It
answered the board's questions from the day it was built, but it duplicated, in SQL, knowledge that the departments'
assistants already had, and it couldn't use their tools.

The second step built what Smarter lacked: a **runtime for Orchestrators**. Its central decision is that a step of
an orchestration is nothing new. It is an ordinary prompt of the department's assistant, run as that assistant's
owner, with its tools, its guardrail and its budget, and recorded in the journal like any other prompt. The person
who starts a run must be allowed to use every assistant in it, or the run is refused before any model is called.
So the chief executive, a member of every department, can run the board pack; the chief financial officer, who is
not a member of HR, can't, and gets a 403 that names the reason.

The board pack now runs as one request, ``Prepare the board pack for Q4 2025.``, in which four departments'
assistants answer in parallel, each from its own records, and Atlas writes the page from their answers.

Background
----------

Stackademy's departments each have an assistant over their own records (see :doc:`confidential-by-construction`):
**Harper** for HR, **Ledger** for Accounting, **Reel** for Course Content and **Ada** for Admissions. Each lives in
its department's account, reads its department's tables through its department's database user, and is charged to
its department's budget of $150 a month.

The executives, in the company's account ``Stackademy Corp``, want a quarterly page for the board: headcount and
hiring, revenue and expenses, the departments over budget, overdue invoices, courses in production, and
enrollments. The chief executive is a member of every department's account; the chief financial officer is a member
of the company's and of Accounting's.

Smarter had an **Orchestrator** kind, whose manifest declares a strategy, a bound on iterations, and *harnesses*:
LLMClients, each with a role and an execution order. Its manifest applied and its models could record a run and its
steps. But nothing executed one, and a harness could name only an LLMClient of the Orchestrator's own account, so
the executives' Orchestrator couldn't reach a department's assistant at all.

The challenge
-------------

1. **No new access.** An orchestration must not let anyone read what they couldn't read by using each assistant
   directly. In particular, the executives must not gain access to individuals' salaries or students' records
   through the board pack.
2. **The departments stay in charge.** Each department's assistant must answer with its own tools and instructions,
   and its cost must land on its department's budget, not on the executives'.
3. **Governed like everything else.** Every model call in a run must pass the same guardrails, budgets and journal
   as a prompt in the console, rather than a second, parallel implementation of them.
4. **Long runs.** A run of five assistants, several of which call tools, takes longer than a web request may wait.
5. **A board pack this quarter**, before the runtime could be designed, built and released.

Options considered
------------------

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Option
     - For
     - Against
   * - Give the executives' assistant the departments' connections
     - One assistant, no new runtime
     - The executives' assistant could read every table that every department may, salaries included: requirement 1
       fails
   * - An assistant over views of totals (**Atlas**, chosen as the interim)
     - Safe by construction: the views return only aggregates; ready in a day
     - Duplicates the departments' knowledge in SQL; can't use their tools or instructions
   * - An agent framework such as LangGraph or CrewAI
     - Mature control flow; many patterns
     - Its own model of agents, tools, memory and state, beside Smarter's LLMClients, plugins, budgets and journal,
       which each step must use to stay governed
   * - Run each step as the person who started the run
     - Simple to explain
     - HR's assistant would read HR's records with the runner's rights, and the charges would land in the runner's
       account instead of the department's
   * - **A runtime in Smarter: each step a prompt, run as its LLMClient's owner** (chosen)
     - Every existing control applies unchanged; the departments' assistants answer as themselves
     - A run's cost is spread over several departments' budgets, and no single budget caps a run

The solution
------------

**The interim: Atlas over views of totals.** The executives' database user reads no table, only five views, each
``SQL SECURITY DEFINER``, so that it runs with its definer's rights and returns only what its ``SELECT`` computes:

.. code-block:: sql

   CREATE OR REPLACE SQL SECURITY DEFINER VIEW `board_headcount` AS
   SELECT d.name AS department, COUNT(e.employee_id) AS headcount, SUM(c.annual_salary) AS annual_payroll
   FROM employees e
   JOIN departments d ON d.department_id = e.department_id
   JOIN compensation c ON c.employee_id = e.employee_id
     AND c.effective_date = (SELECT MAX(c2.effective_date) FROM compensation c2 WHERE c2.employee_id = e.employee_id)
   GROUP BY d.name;

The others total the income statement, budget against actual spending, enrollments and tuition, and course
production. Atlas has a SqlPlugin over each view, and a system role that forbids guessing a number or adding figures
up. It lives in Stackademy Corp, where only the executives may use it.

**The runtime.** ADR-037 sets nine rules. The ones that shaped the board pack:

- **A run is asynchronous.** ``POST /api/v1/orchestrators/<id>/runs/`` with an objective answers ``202`` with the
  run's id; a Celery task executes it; ``GET .../runs/<run_id>/`` returns its status, its steps and its result.
- **A step is a prompt**, through the same handler as an LLMClient's prompt api, in a session of its own per
  harness per run. Tools, guardrails, the journal, charges and budgets apply unchanged.
- **A step runs as its LLMClient's owner.** HR's assistant uses HR's connection and is charged to HR. The person
  who started the run is the *acting user*, so that tools learn who asked.
- **The runner may use every harness**, or the run is refused with 403 before any model is called.
- **A harness may name another account's LLMClient**, with ``accountNumber``. Applying the manifest requires that
  the Orchestrator's owner may read it.
- **Messages between steps are built in code**: the objective, the earlier outputs it depends on, labeled by
  harness, and the harness's own instructions.

.. figure:: /_static/case-studies/board-pack-run.svg
   :alt: The CEO starts a run of the orchestrator stackademy_quarterly_board_pack. Harper, Ledger, Reel and Ada each
         answer in their own account, from their own database user. Atlas, the summarizer, writes the board pack.
   :width: 100%

   Exhibit 1. A run of the quarterly board pack.

**The board pack as an orchestration.** The executives' Orchestrator names each department's assistant in its own
account, gives each the instructions for its section of the page, and makes Atlas the summarizer:

.. code-block:: yaml

   # departments/executive/orchestrators/stackademy-quarterly-board-pack.yaml (abridged)
   kind: Orchestrator
   metadata:
     name: stackademy_quarterly_board_pack
   spec:
     config:
       strategy: parallel
       maxIterations: 5
       harnesses:
         - llmClientName: stackademy_hr_assistant
           accountNumber: "2718-2818-0002"
           role: executor
           executionOrder: 0
           config:
             instructions: >-
               Report on Stackademy's people, the whole company's, for the board, in at most 150 words, with your
               figures in a table: headcount by department, and the positions that we are hiring for. Never name an
               individual's salary.
         - llmClientName: stackademy_accounting_assistant
           accountNumber: "2718-2818-0003"
           role: executor
           executionOrder: 1
           config:
             instructions: >-
               Report on Stackademy's finances for the board, for the period of the objective, ... Don't add figures
               up yourself.
         # Course Content (2718-2818-0004) and Admissions (2718-2818-0005) likewise
         - llmClientName: stackademy_board_pack
           role: summarizer
           executionOrder: 4
           config:
             instructions: >-
               Write the board pack's one page from the departments' answers above: a short section for each, its
               figures in a table, then the three points that most need the board's attention. Quote their figures
               as they are, and check any total with your own tools.

The strategy is ``parallel`` because the departments' sections don't depend on one another: each assistant
receives only the objective and its instructions. Atlas, as summarizer, receives every answer, and keeps its own
tools, so that it can check a department's total against the views.

**Four strategies.** The runtime runs the four strategies that need no voting or debate rules; a run of ``voting``
or ``debate`` is refused with a message that names it.

.. figure:: /_static/case-studies/strategies.svg
   :alt: Four panels. Sequential: each harness sees the answers before it. Parallel: each sees only the objective.
         Router: a router picks one assistant. Supervisor: a planner asks one assistant at a time until it is done.
   :width: 100%

   Exhibit 2. The four orchestration strategies that Smarter runs.

Implementation
--------------

The work was done in this order, so that the executives had a board pack from the first day:

1. **Atlas and the board views** (Stackademy ``639fd76``): the five views, the executives' database user and
   connection, six SqlPlugins, and Atlas, in Stackademy Corp.
2. **ADR-037**, written and agreed before any code: the nine rules above, and the alternatives it rejects.
3. **Sequential and parallel runs** (Smarter ``d14495711``): the run and step models' runtime (``RunPlan``,
   ``RunContext``), the Celery task ``execute_orchestration_run``, which is never retried, since a retry would repeat
   steps that call a model and are charged, the runs api, its Pydantic contract, the migration that records who
   started a run, and harnesses in other accounts.
4. **Supervisor and router runs** (``61c4a01da``), whose coordinators answer in JSON, parsed even when the model
   wraps it in prose or a code block.
5. **The board pack as an orchestration** (Stackademy ``48489dc``), and the web console's **Runs** section, where
   a user starts a run of an Orchestrator and follows its steps as they end (``b22c6cbb3`` lists the user's runs;
   smarter-console 1.1.12).

Two decisions were argued at length. **Who a step runs as**: as the runner, a step would read a department's
records with rights the runner may not have, and charge the runner's account. As the LLMClient's owner, it reads
what the department's assistant always reads, and the department pays for its own work, which is how the budget
was meant to work. **What the runner must be allowed**: running as the owner is safe only if the runner could have
asked each assistant directly, so the run checks that first, for every active harness. Without that check, the
Orchestrator would be a way into every department for anyone who may run it.

Results
-------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Measure
     - Result
   * - Requests to produce a board pack
     - One: ``POST .../runs/`` with the objective, followed in the console's Runs section
   * - Model calls in a run
     - Five: four departments in parallel, then Atlas
   * - Where each step is charged
     - To the department whose assistant did the work, against its own budget
   * - Who may run it
     - The chief executive, a member of every department. The CFO is refused with 403, before any model is called
   * - New access granted to anyone
     - None: a run reaches only assistants its runner could use directly
   * - Controls implemented twice
     - None: guardrails, tools, budgets and the journal apply to each step as to any prompt
   * - Strategies
     - Sequential, parallel, router and supervisor run; voting and debate are refused, to be designed separately

The interim also found something no one was looking for. Comparing Atlas's figures with the departments' revealed
four errors in how the company's figures were computed and reported, one of them in every board pack. That is the
subject of :doc:`when-the-numbers-dont-add-up`.

Lessons for practitioners
-------------------------

- **An orchestration is an access path.** Before asking what agents can do together, ask whose rights each one
  uses, and who may set them going.
- **Run each agent as itself.** A step that runs as its own owner keeps the department's controls and its costs
  where they belong. Then check that the caller could have asked each one directly.
- **Don't build a second control plane.** Making each step an ordinary prompt meant that guardrails, budgets and
  the journal needed no orchestration-specific code, and can't drift from the real ones.
- **Ship a safe interim.** Views of totals gave the executives a board pack at once, with no new access, and made
  the runtime a decision rather than an emergency.
- **Choose the simplest strategy that fits.** The board's sections don't depend on each other, so ``parallel``
  suffices; a supervisor would add model calls, cost and nondeterminism without adding anything the page needs.

Teaching notes
--------------

**Discussion questions**

1. The CFO is refused because they aren't a member of HR. Is that the right outcome for a CFO? List three ways to
   give the CFO a board pack, and the access each grants.
2. A run's cost is spread over the departments' budgets, and no single budget caps a run. Who should pay for the
   board pack: the departments, or the executives? How would you implement your answer?
3. Atlas checks the departments' totals with its own tools. What happens when they disagree? Read
   :doc:`when-the-numbers-dont-add-up` after you answer.
4. When would ``supervisor`` be worth its cost for a board pack? Describe a question that ``parallel`` can't answer
   well.

**Exercises**

1. On a platform with Stackademy loaded, sign in as ``vera_jaramillo`` and run the board pack for Q4 2025 from the
   Orchestrator's page. Open each step's prompt session and identify which tools each department's assistant
   called.
2. Sign in as ``odette_hartigan`` (CFO) and try the same run. Record the response, and find the rule in ADR-037
   that produces it.
3. Copy the Orchestrator, change its strategy to ``sequential``, and run it. Compare the two runs: which
   department's answer changed, and why?
4. Write a ``router`` Orchestrator for the executives that sends a question to the one department that can answer
   it, with a router LLMClient of your own. Test it with three questions, one of which no department can answer.

Sources
-------

- :doc:`ADR-037: Orchestration Runtime </adr/037-orchestration-runtime>`
- :doc:`/smarter-resources/smarter-orchestrator`
- ``smarter/smarter/apps/orchestrator/runtime.py``, ``tasks/__init__.py`` and ``api/v1/views/``
- Smarter commits ``d14495711``, ``61c4a01da`` and ``b22c6cbb3``; smarter-console 1.1.12
- The Stackademy repository, ``departments/executive/`` and ``scripts/generate_backoffice.py`` (``BOARD_VIEWS``):
  https://github.com/smarter-sh/stackademy; commits ``639fd76`` and ``48489dc``
