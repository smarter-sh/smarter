Building AI Applications: Classroom Bootcamp
============================================

An eight-hour classroom bootcamp on the architecture of AI applications: retrieval, tool calling,
structured data, MCP servers and multi-agent workflows. Every component is a resource declared in
a YAML manifest, so the bootcamp covers the whole landscape without teaching a programming
language. See :doc:`../course-formats` for the standard bootcamp day, the grading scale and the
course policies, and :doc:`../ai-applications` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Product managers, analysts, designers, consultants and developers who want to understand
       how AI applications are put together.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with a
       :doc:`Vectorstore </smarter-resources/smarter-vectorstore>` backend, a sample database
       behind a :doc:`Connection </smarter-resources/smarter-connection>`, and one or two
       :doc:`MCP clients </smarter-resources/smarter-mcpclient>` set up in advance.
   * - **Cost**
     - Expect less than $3 USD of model charges per student, plus any vector database charges,
       capped by a per-student :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Describe the parts of an AI application: model, instructions, knowledge, tools, guardrails and
   orchestration.
2. Build a retrieval-augmented assistant that answers from documents, with citations.
3. Let a model answer questions about structured data, and explain the risks of doing so.
4. Connect an assistant to external systems through plugins and MCP servers.
5. Compare a single assistant with an orchestrated workflow on cost, latency and quality.

Technical Prerequisites
-----------------------

- **Required:** a laptop with a current web browser, and experience of using a chat assistant.
- **Required:** reading and editing YAML (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__) and reading JSON.
- **Required:** basic understanding of what a database table and a web API are. No SQL needed.
- **Helpful:** the :doc:`Prompt Engineering <../prompt-engineering>` course or equivalent
  experience writing system prompts.
- **Not needed:** programming.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: Anatomy of an AI application.** The model, the system prompt, knowledge,
       tools, guardrails and orchestration, and how each appears as a Smarter resource. A tour of
       the built-in ``simple``, ``customer_support`` and ``research_analyst`` LLMClients, from a bare
       model to a complete application.
   * - 2
     - 45
     - **Lab 1: Read an application.** In pairs, take the ``research_analyst`` manifest apart:
       list every resource it uses, what each does, and draw how a question flows through it.
       Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Retrieval.** Why models make things up. Embeddings and similarity search
       explained without mathematics, chunking, and citations.
       :doc:`Vectorstores </smarter-resources/smarter-vectorstore>` in Smarter.
   * - 4
     - 45
     - **Lab 2: A teaching assistant.** Load a course syllabus and handbook into a Vectorstore,
       and build an LLMClient that answers questions about them with citations. Produces
       Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Structured data.** Text-to-SQL with a :doc:`SQL Plugin </smarter-resources/plugin/plugin/sql>`
       and a :doc:`Connection </smarter-resources/smarter-connection>`. Read-only access, why the
       model never sees the database password, and how wrong answers happen. The built-in
       ``data_analyst`` LLMClient as a worked example.
   * - 6
     - 45
     - **Lecture 4: Tools and MCP.** Function calling, :doc:`API </smarter-resources/plugin/plugin/api>`
       and :doc:`Websearch </smarter-resources/plugin/plugin/websearch>` plugins, and the
       `Model Context Protocol <https://modelcontextprotocol.io/>`__.
       :doc:`MCP clients </smarter-resources/smarter-mcpclient>` in Smarter.
   * - 7
     - 45
     - **Lab 3: A data assistant.** Build an assistant that answers five business questions in
       plain English over a sample database, and check each answer against the true figure.
       Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Orchestration.** Workflows and agents, routing, and when several specialized
       assistants beat one general one. The :doc:`Orchestrator </smarter-resources/smarter-orchestrator>`
       resource.
   * - 9
     - 45
     - **Lab 4: One assistant or several?** Build a two-step workflow (for example research, then
       write) as one LLMClient and as an Orchestrator, and compare tokens, time and output.
       Ungraded.
   * - 10
     - 45
     - **Lecture 6: Production concerns.** Guardrails, budgets, the journal, evaluation and
       deployment. What changes when real users arrive.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone, sketch its architecture diagram and get
       feedback.

Graded Assignments
------------------

Assignment 1: Architecture Teardown
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students document how the built-in ``research_analyst`` LLMClient works: every resource it
references, what each contributes, and the path of one question through the system, confirmed by
the Console's view of the tool calls.

**Turn in:** a one-page diagram and a half-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 6
     - Every resource in the manifest is identified, with its role.
     - Some resources missing, or roles confused.
   * - Data flow
     - 6
     - Diagram shows the order of model calls, tool calls and results.
     - A list of boxes with no flow.
   * - Evidence
     - 4
     - The flow is confirmed against real tool calls in the Console.
     - Inferred from the manifest only.
   * - Clarity
     - 4
     - A newcomer could follow the diagram.
     - Unlabeled or cluttered.

Assignment 2: Retrieval Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build an assistant over a set of documents, and test it with ten questions that the
documents answer and three that they do not.

**Turn in:** the manifests, the list of documents, and the test results with citations.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Working retrieval
     - 6
     - Answers draw on the right passages.
     - Retrieval runs, but answers ignore it.
   * - Citations
     - 5
     - Each answer names its source document.
     - Citations missing or invented.
   * - Unanswerable questions
     - 5
     - The assistant says that it does not know.
     - The assistant invents answers.
   * - Testing
     - 4
     - All thirteen results reported honestly.
     - Results incomplete.

Assignment 3: Data Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build an assistant over the sample database, ask it five business questions in plain
English, and check each answer against the true figure, which the instructor provides.

**Turn in:** the manifests, the questions, the assistant's answers and generated SQL from the
Console, and the check against the true figures.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Configuration
     - 5
     - Plugin and connection configured with read-only access.
     - Works, but with unnecessary access.
   * - Accuracy check
     - 6
     - Every answer checked against the true figure.
     - Answers accepted without checking.
   * - Failure analysis
     - 5
     - Wrong answers are explained from the generated SQL.
     - Wrong answers noted but not explained.
   * - Improvement
     - 4
     - System prompt or plugin description changed to fix one failure.
     - No attempt to fix failures.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Knowledge Assistant for an Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design and build a grounded assistant that combines retrieval with at least
one tool, and show with evidence that it is accurate.

Students pick an organization (real, with permission, or fictional with realistic documents) and
build an assistant that answers questions from its documents and takes one action, such as
searching the web for current information or calling a public API.

**What students turn in:**

- The manifests, and the documents or links to them.
- An architecture diagram and a one-page design note.
- A test set of twenty questions with results, including questions that the documents do not
  answer.
- A five-minute recorded or live demonstration.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Architecture
     - 20
     - Each component is chosen for a stated reason, and the diagram matches the build.
     - Components added without reason.
   * - Grounding
     - 25
     - Accurate, cited answers, and honest "I don't know" answers.
     - Invents answers when documents are silent.
   * - Tool use
     - 15
     - The tool is called when needed, and its result is used.
     - Tool configured but unused.
   * - Testing
     - 25
     - Twenty varied questions, with failures reported and explained.
     - Few or easy questions.
   * - Demonstration
     - 15
     - Shows a retrieval, a tool call and a refusal, clearly and on time.
     - Shows only easy chat.

Capstone B: Single Assistant versus Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Decide on evidence whether a job needs a multi-step workflow or a single
assistant.

Students choose a job with clear steps, such as screening job applications against criteria and
drafting replies, or researching a topic and writing a briefing. They build it as one LLMClient
and as an Orchestrator of two or three specialized ones, and compare the two on ten inputs.

**What students turn in:**

- The manifests for both designs.
- The ten inputs, a scoring rubric, and a table of quality scores, tokens, cost and response time.
- A two-page recommendation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Both designs work
     - 25
     - Both produce complete outputs on all ten inputs.
     - One design is incomplete.
   * - Fair comparison
     - 20
     - Same inputs, same model, comparable effort on each design.
     - One design clearly neglected.
   * - Measurements
     - 20
     - Quality scored with a rubric, cost and time from Smarter's records.
     - Impressions instead of measurements.
   * - Analysis
     - 20
     - Explains where each design wins and why.
     - Names a winner without explanation.
   * - Recommendation
     - 15
     - A clear, conditional recommendation ("use the workflow when...").
     - No recommendation.

Recommended Texts
-----------------

- **Pre-reading:** Anthropic, `Building effective agents
  <https://www.anthropic.com/engineering/building-effective-agents>`__ (2024). A 20-minute read.
- **Reference:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025). Chapter 6, on retrieval and agents, is the best follow-up to the bootcamp.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-vectorstore`,
  :doc:`/smarter-resources/smarter-mcpclient`, :doc:`/smarter-resources/smarter-connection`,
  :doc:`/smarter-resources/plugin/plugin/sql` and :doc:`/smarter-resources/smarter-orchestrator`.

Further Study
-------------

.. include:: further-study.txt
