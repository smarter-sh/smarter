Building AI Applications: Two-Week Online Course
================================================

A two-week online course on the architecture of AI applications: retrieval, tool calling, structured
data, MCP servers and multi-agent workflows, each a resource declared in a YAML manifest. Students
work on the resources that ship with every Smarter installation: `nineteen built-in LLMClients
<https://github.com/smarter-sh/example-manifests/tree/main/llm-clients>`__,
from the bare ``simple`` assistant to ``research_analyst``, which searches the web through an `Exa
MCP server
<https://github.com/smarter-sh/example-manifests/blob/main/mcp-clients/exa.yaml>`__,
reads pages and PDFs, and checks its citations with guardrails; `twenty-eight MCP clients
<https://github.com/smarter-sh/example-manifests/tree/main/mcp-clients>`__
for services such as GitHub, Notion and Stripe; `Vectorstores
<https://github.com/smarter-sh/example-manifests/tree/main/vectorstores>`__
on Qdrant and Pinecone; and an :doc:`Orchestrator </smarter-resources/smarter-orchestrator>` with
six coordination strategies. There are six 30-minute recorded lectures and a 90-minute live session
each week. Week 1 covers knowledge (retrieval and structured data), and week 2 covers action (tools,
MCP and orchestration). See :doc:`../course-formats` for the format, the grading scale and the
course policies, and :doc:`../ai-applications` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Product managers, analysts, designers, consultants and developers.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with a Vectorstore backend, a sample
       database behind a :doc:`Connection </smarter-resources/smarter-connection>`, and one or two
       MCP clients set up in advance.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $6 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Describe the parts of an AI application and how they fit together.
2. Build retrieval-augmented assistants that answer from documents, with citations.
3. Let a model query structured data safely, and check its answers.
4. Connect an assistant to external systems with plugins and MCP servers.
5. Choose between a single assistant and an orchestrated workflow on evidence.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser and a reliable connection for video calls.
- **Required:** reading and editing YAML (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__) and reading JSON.
- **Required:** a general idea of what a database table and a web API are.
- **Helpful:** experience writing system prompts, from the
  :doc:`Prompt Engineering <../prompt-engineering>` course or elsewhere, a GitHub account, and
  basic SQL for reading queries.
- **Not needed:** programming.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **Anatomy of an AI application.** Model, instructions, knowledge, tools, guardrails and
       orchestration as Smarter resources. A tour from ``simple`` to ``research_analyst``.
   * - 1
     - Lecture 2 (30 min)
     - **Retrieval.** Embeddings, similarity search, chunking and citations, without mathematics.
       Building a :doc:`Vectorstore </smarter-resources/smarter-vectorstore>`.
   * - 1
     - Lecture 3 (30 min)
     - **Structured data.** Two safe patterns, both shipped with Smarter: a :doc:`SQL Plugin
       </smarter-resources/llmtool/plugin/sql>` runs a fixed, parameterized query that the model can
       only fill in (`stackademy_sql
       <https://github.com/smarter-sh/stackademy/blob/main/plugins/sql/stackademy-sql.yaml>`__),
       and a SkillPlugin teaches the model a schema so that it writes SQL for a person to review
       (the ``data_analyst`` LLMClient). A :doc:`Connection </smarter-resources/smarter-connection>`
       with a read-only database user, its password in a :doc:`Secret
       </smarter-resources/smarter-secret>`, and how wrong answers still happen.
       Pre-reading: the case study `Stackademy Online Coding Academy
       <https://smarter.sh/case-studies/stackademy>`__, whose "Lab 1: Talk to Stanley" asks the
       same questions of a SQL Plugin advisor and an API Plugin advisor.
   * - 1
     - Live session 1 (90 min)
     - Live build of a teaching assistant over a syllabus. In groups, students find questions that
       break it, and diagnose why. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Tools.** Function calling, :doc:`API </smarter-resources/llmtool/plugin/api>` and
       :doc:`Websearch </smarter-resources/llmtool/plugin/websearch>` plugins. Plugin selection by
       search terms decides which tools Smarter offers, and their descriptions steer which ones
       the model calls (:doc:`/smarter-resources/llmtool/nlp`). :doc:`Extensions
       </smarter-framework/extensibility>`, such as the official weather and calculator tools,
       are installed by an administrator and offered on every prompt of an LLMClient that lists
       them.
   * - 2
     - Lecture 5 (30 min)
     - **MCP.** The `Model Context Protocol <https://modelcontextprotocol.io/>`__, its servers and
       tools, and :doc:`MCP clients </smarter-resources/smarter-mcpclient>` in Smarter.
       Pre-reading: the case study `The Smarter Project MCP Server
       <https://smarter.sh/case-studies/mcp-server>`__, whose "Lab 1: Talk to Sam"
       and "Lab 3: The MCPClient" show an assistant grounded in an MCP server's tools, and its
       manifest.
   * - 2
     - Lecture 6 (30 min)
     - **Orchestration and production.** Workflows versus agents, the
       :doc:`Orchestrator </smarter-resources/smarter-orchestrator>`, guardrails, budgets and
       evaluation.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions), then a
       discussion: which architectures appeared, and why.

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Retrieval Assistant with Evaluation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build an assistant over at least five documents of their choice, test it with fifteen
questions (twelve answerable, three not), and adjust the system prompt once to improve the
results.

**Turn in:** the manifests, the documents or links, and before-and-after results with citations.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Retrieval and citations
     - 6
     - Answers draw on, and name, the right documents.
     - Answers ignore retrieval, or invent sources.
   * - Unanswerable questions
     - 4
     - The assistant admits when it does not know.
     - The assistant invents answers.
   * - Improvement
     - 6
     - One targeted change, with its measured effect.
     - Changes without before-and-after results.
   * - Reporting
     - 4
     - Honest and complete.
     - Incomplete or inflated.

Assignment 2: Data Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build an assistant over the sample database, ask eight business questions, and check
each answer, and the SQL behind it, against the true figure.

**Turn in:** the manifests, the questions, answers, the SQL behind each one, and a short failure
analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Configuration
     - 4
     - Read-only connection; credentials kept in a Secret.
     - Works, but with unnecessary access.
   * - Accuracy check
     - 6
     - Every answer checked against the truth.
     - Answers accepted without checking.
   * - Failure analysis
     - 6
     - Wrong answers explained from the SQL, with a fix tried.
     - Wrong answers noted, not explained.
   * - Risk note
     - 4
     - Names what could go wrong if real managers relied on it, and a mitigation.
     - No discussion of risk.

Assignment 3: A Tool-Using Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students give an assistant two tools: one plugin (API or Websearch) and one MCP client provided by
the instructor. They show conversations in which the model uses each tool, one in which it
correctly uses neither, and explain what decided the model's choice.

**Turn in:** the manifests, three Console screenshots, and a one-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Both tools work
     - 6
     - Each tool is called and its result used.
     - One tool never called.
   * - Restraint
     - 4
     - A conversation where no tool is needed and none is called.
     - Tools called for every message.
   * - Explanation
     - 6
     - Links the model's choices to the tool descriptions and system prompt.
     - Describes what happened without explaining why.
   * - Safety
     - 4
     - Notes what each tool could do if misused, and how it is limited.
     - No discussion of safety.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Knowledge and Action Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Combine retrieval, structured data or tools into one coherent assistant for
a defined user, and show that it is accurate and safe.

Students design an assistant for a real or realistic user, such as a new employee onboarding
assistant, a club treasurer's helper, or a course advisor. It must use retrieval and at least one
of a SQL Plugin, an API Plugin or an MCP client, and at least one guardrail.

**What students turn in:**

- A Git repository with every manifest, and a ``README.md``.
- An architecture diagram and a two-page design note that justifies each component.
- A test set of twenty-five questions with results.
- A five-minute presentation with a live demonstration.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Architecture
     - 25
     - Each component justified by the user's needs; the diagram matches the build.
     - Components added because they were available.
   * - Accuracy
     - 25
     - Grounded, cited and correct answers; honest about gaps.
     - Correct on easy questions only.
   * - Safety
     - 15
     - Guardrails and access limits match the risks.
     - A guardrail unrelated to the risks.
   * - Testing
     - 20
     - Twenty-five varied questions, failures reported and explained.
     - Few or easy questions.
   * - Presentation
     - 15
     - Clear, on time, shows design decisions.
     - Shows chat only.

Capstone B: Architecture Comparison Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Compare alternative architectures for the same job, and recommend one on
evidence of cost, latency and quality.

Students choose a job, such as answering questions about a product catalog. They build it three
ways: a single LLMClient with documents in a Static Plugin, a retrieval-based LLMClient with a
Vectorstore, and an Orchestrator of specialized LLMClients. They evaluate all three on fifteen
inputs.

**What students turn in:**

- A Git repository with all three designs.
- The inputs, rubric and a table of scores, tokens, cost and response time.
- A three-page report with charts and a recommendation.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Three working designs
     - 25
     - All three complete every input.
     - One or more incomplete.
   * - Fair evaluation
     - 20
     - Same inputs, model and rubric for all three.
     - Inconsistent conditions.
   * - Measurements
     - 20
     - From Smarter's records; repeated where results vary.
     - Estimated or partial.
   * - Analysis and recommendation
     - 25
     - Explains the trade-offs and when each design is right.
     - A winner without reasons.
   * - Presentation
     - 10
     - Clear and on time.
     - Overruns or unclear.

Recommended Texts
-----------------

- **Required:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025). Week 1: chapters 1 and 6 (retrieval). Week 2: chapter 6 (agents) and chapter
  10.
- **Required:** Anthropic, `Building effective agents
  <https://www.anthropic.com/engineering/building-effective-agents>`__ (2024), before Lecture 6.
- **Optional:** Jay Alammar and Maarten Grootendorst, *Hands-On Large Language Models* (O'Reilly,
  2024), chapter 8 on semantic search and retrieval, for students who want the mechanics.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-vectorstore`,
  :doc:`/smarter-resources/smarter-mcpclient`, :doc:`/smarter-resources/smarter-connection`,
  :doc:`/smarter-resources/llmtool/plugin/sql` and :doc:`/smarter-resources/smarter-orchestrator`.

Further Study
-------------

.. include:: further-study.txt
