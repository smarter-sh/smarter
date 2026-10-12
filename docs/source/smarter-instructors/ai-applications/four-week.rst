Building AI Applications: Four-Week Online Course
=================================================

A four-week online course on the architecture of AI applications, with twelve 30-minute recorded
lectures and a 90-minute live session each week. Week 1 covers the building blocks, week 2
knowledge, week 3 action, and week 4 orchestration and production. See :doc:`../course-formats`
for the format, the grading scale and the course policies, and :doc:`../ai-applications` for an
overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Product managers, analysts, designers, consultants and developers.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with a Vectorstore backend, a sample
       database behind a :doc:`Connection </smarter-resources/smarter-connection>`, and two or
       three MCP clients set up in advance.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $12 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Describe the parts of an AI application, and choose the right ones for a job.
2. Build and tune retrieval-augmented assistants, and measure their accuracy.
3. Let a model query structured data safely, and check its answers.
4. Connect an assistant to external systems with plugins and MCP servers, and limit what they can
   do.
5. Design orchestrated workflows, and decide on evidence when they are worth their cost.
6. Evaluate, govern and present an AI application as a product.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser and a reliable connection for video calls.
- **Required:** reading and editing YAML (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__) and reading JSON.
- **Required:** a general idea of what a database table and a web API are.
- **Required by week 2:** a GitHub account, and enough Git to commit files through the web
  interface or `GitHub Desktop <https://desktop.github.com/>`__.
- **Helpful:** experience writing system prompts, basic SQL, and a spreadsheet program.
- **Not needed:** programming.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1
     - **Anatomy of an AI application.** Model, instructions, knowledge, tools, guardrails and
       orchestration as Smarter resources.
   * - 1
     - Lecture 2
     - **Models and prompts for applications.** Choosing a model, system prompts that stay on task,
       and structured output that other systems can use.
   * - 1
     - Lecture 3
     - **Reading manifests.** A guided tour of ``customer_support``, ``research_analyst`` and
       ``data_analyst``: what each resource adds, confirmed in the Console.
   * - 1
     - Live session 1
     - Architecture teardown in groups, then a short live build. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Retrieval, part 1.** Embeddings, similarity search and citations, without mathematics.
       Building a :doc:`Vectorstore </smarter-resources/smarter-vectorstore>`.
   * - 2
     - Lecture 5
     - **Retrieval, part 2.** Chunking, top-k, metadata, stale documents, and measuring retrieval
       quality separately from answer quality.
   * - 2
     - Lecture 6
     - **Structured data.** Text-to-SQL with a :doc:`SQL Plugin </smarter-resources/plugin/plugin/sql>`,
       read-only connections, credentials in :doc:`Secrets </smarter-resources/smarter-secret>`,
       and checking generated queries.
   * - 2
     - Live session 2
     - Review of Assignment 1. Diagnose retrieval failures as a class. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Tools.** Function calling, :doc:`API </smarter-resources/plugin/plugin/api>` and
       :doc:`Websearch </smarter-resources/plugin/plugin/websearch>` plugins, and tool
       descriptions.
   * - 3
     - Lecture 8
     - **MCP.** The `Model Context Protocol <https://modelcontextprotocol.io/>`__ and
       :doc:`MCP clients </smarter-resources/smarter-mcpclient>`: authentication, tool selection,
       and trusting a server.
   * - 3
     - Lecture 9
     - **Tool safety.** What a tool can do if the model is tricked. Prompt injection through
       retrieved content, least privilege, and :doc:`Guardrails </smarter-resources/smarter-guardrail>`.
   * - 3
     - Live session 3
     - Review of Assignment 2. Students attack each other's tool-using assistants with injected
       content. Capstone proposals discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Orchestration.** Workflows, routing, agents and the
       :doc:`Orchestrator </smarter-resources/smarter-orchestrator>`.
   * - 4
     - Lecture 11
     - **Evaluation.** Test sets, rubrics, LLM judges, and regression testing an application.
   * - 4
     - Lecture 12
     - **Production.** Budgets, cost accounting, the journal, deployment, and what changes when
       real users arrive.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Graded Assignments
------------------

Assignment 1: Architecture Teardown
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students document two built-in LLMClients: every resource each one uses, its role, and the path of
one question, confirmed in the Console. They finish with a paragraph on why the two designs
differ.

**Turn in:** two diagrams and a one-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 6
     - Every resource identified with its role.
     - Resources missing or confused.
   * - Data flow
     - 6
     - Order of model calls, tool calls and results shown, and confirmed in the Console.
     - Boxes without flow, or inferred only.
   * - Comparison
     - 4
     - Explains the design differences by the jobs the assistants do.
     - Lists differences without explanation.
   * - Clarity
     - 4
     - A newcomer could follow it.
     - Cluttered or unlabeled.

Assignment 2: Measured Retrieval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build a Vectorstore over at least ten documents, write twenty questions with the passage
that answers each, and measure two things separately: whether the right passage was retrieved, and
whether the answer was right. They try one change to improve each.

**Turn in:** manifests, the question set with expected passages, before-and-after measurements,
and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Question set
     - 5
     - Varied questions, each linked to the passage that answers it.
     - Questions without expected passages.
   * - Two measurements
     - 6
     - Retrieval and answer quality measured separately.
     - Only answers checked.
   * - Improvements
     - 5
     - One change per measurement, with its effect.
     - Changes without measured effect.
   * - Analysis
     - 4
     - Explains which failures were retrieval and which were generation.
     - Does not distinguish them.

Assignment 3: Data Assistant with a Risk Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build an assistant over the sample database, check ten answers against the truth, and
write a risk review of what could go wrong if managers relied on it, with mitigations they
implement.

**Turn in:** manifests, the questions, answers, generated SQL and checks, and a two-page risk
review.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Configuration
     - 4
     - Read-only connection, credentials in a Secret.
     - Unnecessary access, or credentials in the manifest.
   * - Accuracy
     - 6
     - All ten checked; failures explained from the SQL.
     - Answers accepted unchecked.
   * - Risk review
     - 6
     - Specific risks, ranked by likelihood and impact.
     - Generic risks of AI.
   * - Mitigations
     - 4
     - At least two mitigations implemented and shown working.
     - Mitigations proposed but not implemented.

Assignment 4: Tools Under Attack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build an assistant with a Websearch or API plugin and an MCP client, then try to make it
misuse a tool through prompt injection, including instructions hidden in a web page or document
that it reads. They add defenses and repeat the attacks.

**Turn in:** manifests, an attack log from the journal before and after the defenses, and a
one-page report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Working tools
     - 4
     - Both tools called when appropriate.
     - One tool never used.
   * - Attacks
     - 6
     - Direct and indirect injection attempts, at least eight in total.
     - Direct attacks only.
   * - Defenses
     - 6
     - Guardrails and narrower tool access stop most attacks, shown in the second log.
     - Defenses added but not re-tested.
   * - Report
     - 4
     - Explains what still gets through, honestly.
     - Claims complete protection.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: An AI Product for a Real User
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Take an AI application from a user's need to an evaluated, governed and
deployed product, and present it as a product manager would.

Students interview a real user and build an application with retrieval, at least one tool, at
least two guardrails, a budget, and an Orchestrator if the job has distinct steps. The instructor
deploys it so that the user can try it.

**What students turn in:**

- A Git repository with every manifest and a ``README.md`` for maintainers.
- A three-page product brief: the user, the job, the architecture with a diagram, the risks and
  their controls, and the expected monthly cost.
- An evaluation with at least thirty test cases, a rubric and results.
- Written feedback from the user.
- A six-minute presentation with a live demonstration.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - User fit
     - 15
     - The design follows from the interview; feedback is addressed.
     - Generic application.
   * - Architecture
     - 20
     - Each component justified; orchestration used only where it helps.
     - Components added because they exist.
   * - Accuracy and evaluation
     - 25
     - Thirty varied tests, honest results, failures addressed.
     - Few tests, or results that did not change the design.
   * - Governance and cost
     - 20
     - Guardrails and budget match the risks; cost projected from measurements.
     - Controls unrelated to risks; cost guessed.
   * - Presentation
     - 20
     - Clear, on time, persuasive to a non-technical audience.
     - Technical walkthrough with no product story.

Capstone B: An Agentic Workflow with an Evaluation Suite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a multi-step workflow, prove with an evaluation suite that each step
and the whole work, and decide where a single assistant would do.

Students choose a job with at least three distinct steps, such as reading a support ticket,
looking up the customer's records and drafting a reply, or researching, outlining and writing a
briefing. They build it as an Orchestrator of specialized LLMClients with tools, and as a single
LLMClient, and evaluate both.

**What students turn in:**

- A Git repository with both designs.
- An evaluation suite: test cases for each step and end-to-end, a rubric, and a validated judge
  LLMClient.
- Results for both designs, with cost and latency.
- A three-page report and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Workflow design
     - 20
     - Steps are well bounded, with clear inputs and outputs.
     - Steps overlap, or one step does everything.
   * - Evaluation suite
     - 25
     - Tests per step and end-to-end; judge validated against human scores.
     - End-to-end tests only; judge unchecked.
   * - Comparison
     - 20
     - Fair comparison with the single assistant, on quality, cost and latency.
     - Single assistant neglected.
   * - Robustness
     - 15
     - Handles bad inputs and tool failures gracefully.
     - Fails silently when a tool fails.
   * - Report and presentation
     - 20
     - Clear recommendation with trade-offs.
     - Results without a recommendation.

Recommended Texts
-----------------

- **Required:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025). Week 1: chapters 1 and 2. Week 2: chapter 6 (retrieval). Week 3: chapter 6
  (agents). Week 4: chapters 3, 4 and 10.
- **Required:** Anthropic, `Building effective agents
  <https://www.anthropic.com/engineering/building-effective-agents>`__ (2024), before Lecture 10.
- **Optional:** Jay Alammar and Maarten Grootendorst, *Hands-On Large Language Models* (O'Reilly,
  2024), chapters 2 and 8, for the mechanics of embeddings and retrieval.
- **Optional:** Paul Iusztin and Maxime Labonne, *LLM Engineer's Handbook* (Packt, 2024), for
  students who go on to build applications in code.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-vectorstore`,
  :doc:`/smarter-resources/smarter-mcpclient`, :doc:`/smarter-resources/smarter-connection`,
  :doc:`/smarter-resources/plugin/plugin/sql`, :doc:`/smarter-resources/smarter-orchestrator`,
  :doc:`/smarter-resources/smarter-guardrail` and :doc:`/smarter-platform/cost-accounting`.

Further Study
-------------

.. include:: further-study.txt
