Building AI Applications
========================

**Why Smarter.** An AI application is more than a model: it is a model plus instructions, knowledge,
tools, guardrails and, increasingly, other models. Most courses can show these parts only one at a
time, in a different framework each, and only to students who can program. In Smarter, each part is
a resource declared in a short YAML manifest, with the same ``apply``, ``describe`` and ``delete``
lifecycle: :doc:`Vectorstores </smarter-resources/smarter-vectorstore>` on Qdrant or Pinecone for
retrieval, :doc:`SQL </smarter-resources/llmtool/plugin/sql>` and :doc:`API
</smarter-resources/llmtool/plugin/api>` plugins over a :doc:`Connection
</smarter-resources/smarter-connection>` for structured data, :doc:`MCP clients
</smarter-resources/smarter-mcpclient>` for the tools of any MCP server, :doc:`Guardrails
</smarter-resources/smarter-guardrail>` for safety, and an :doc:`Orchestrator
</smarter-resources/smarter-orchestrator>` for multi-agent workflows. A course can cover the whole
landscape of AI application architecture in a term, without first teaching a programming language.

Students learn from complete, working applications, not diagrams. Every installation ships with
`nineteen built-in LLMClients
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmclient/data/llm-clients>`__
to take apart, such as `research_analyst
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/data/llm-clients/llmclient-research-analyst.yaml>`__,
which searches the web through the Exa MCP server, reads pages and PDFs, and checks its citations
with an output guardrail; `twenty-five ready-made MCP clients
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/mcpclient/data/mcpclients>`__
for services such as GitHub, Notion, Linear and Stripe; twenty `sample plugins
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/data/sample-plugins>`__;
and `Stackademy <https://github.com/smarter-sh/stackademy>`__, a fictional online code academy whose
course catalog is served both from a database and from a REST API, and whose manifests are a git
repository of their own.

Smarter also makes the design decisions behind safe AI applications visible, where students can
see them and argue about them:

- A tool is used only after two decisions: Smarter
  :doc:`selects a plugin </smarter-resources/llmtool/nlp>` when the prompt matches its search
  terms, and only then does the model decide whether to call it.
- A SQL Plugin runs a fixed, `parameterized query
  <https://github.com/smarter-sh/stackademy/blob/main/plugins/sql/stackademy-sql.yaml>`__
  that the model can only fill in, so the model never writes SQL that runs. The ``data_analyst``
  LLMClient shows the other pattern: a skill that teaches the model a schema, so that it writes SQL
  for a person to review.
- Credentials are :doc:`Secrets </smarter-resources/smarter-secret>`, named in a manifest but
  never shown to the model, and MCP connections are `restricted
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/mcpclient/connection.py>`__
  to public https endpoints, with an allow-list of the tools the model may use.
- An Orchestrator coordinates several LLMClients with one of six `strategies
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/orchestrator/enum.py>`__:
  sequential, parallel, supervisor, router, voting and debate.
- Every request is :doc:`charged </smarter-platform/cost-accounting>` with its tokens, so students
  can compare one assistant with a workflow of several by cost and latency, as well as quality.

**What the course covers.** The anatomy of an AI application, and how each part appears as a
Smarter resource; models and prompts for applications, including structured output; retrieval:
embeddings, chunking, top-k, citations and measuring retrieval quality; structured data, and the
safe patterns for letting a model answer from a database; tools, function calling, plugin
selection and installed Extensions; the Model Context Protocol, and trusting an MCP server; tool safety and prompt
injection through retrieved content; orchestration, from workflows to agents; evaluation with test
sets, rubrics and LLM judges; and the production concerns of guardrails, budgets, cost accounting,
the journal and deployment.

**Look at.**

- `llmclient/data/llm-clients/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmclient/data/llm-clients>`__,
  especially ``customer_support``, ``research_analyst`` and ``data_analyst``.
- `mcpclient/data/mcpclients/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/mcpclient/data/mcpclients>`__
  and `llmtool/data/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/data>`__.
- `vectorstore/data/vectorstores/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/vectorstore/data/vectorstores>`__,
  one manifest for each kind of vector database.

Each course plan lists every manifest and file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-resources/smarter-vectorstore`,
:doc:`/smarter-resources/smarter-vectorsearch`, :doc:`/smarter-resources/smarter-mcpclient`,
:doc:`/smarter-resources/smarter-connection`, :doc:`/smarter-resources/llmtool/plugin/sql`,
:doc:`/smarter-resources/smarter-orchestrator`, :doc:`/smarter-resources/llmtool/nlp`.

**Exercises.**

- Take the ``research_analyst`` manifest apart: list every resource it uses, what each does, and
  draw how a question flows through it. Confirm each step in the workbench's Console.
- Load a course syllabus and handbook into a Vectorstore, and build a teaching assistant that
  answers questions about them, with citations.
- Answer business questions in plain English over the Stackademy database, with the
  ``stackademy_sql`` SQL Plugin, and compare it with the ``data_analyst`` LLMClient, which writes
  SQL for a person to review. Which would you let a manager rely on, and why?
- Build the same workflow as a single LLMClient and as an Orchestrator of several, and compare
  cost, latency and quality.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <ai-applications/bootcamp>
   Two-week online course: 6 hours <ai-applications/two-week>
   Four-week online course: 12 hours <ai-applications/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
