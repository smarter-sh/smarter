Building AI Applications
========================

**Why Smarter.** Retrieval, tool calling, MCP and multi-agent workflows are each a resource that is
declared in a manifest, so a course can cover the whole landscape of AI application architecture
in a term, without first teaching a programming language.

**Read.** :doc:`/smarter-resources/smarter-vectorstore`, :doc:`/smarter-resources/smarter-mcpclient`,
:doc:`/smarter-resources/smarter-connection`, :doc:`/smarter-resources/plugin/plugin/sql`,
:doc:`/smarter-resources/smarter-orchestrator`.

**Exercises.**

- Load a course syllabus and handbook into a Vectorstore, and build a teaching assistant that
  answers questions about them, with citations.
- Answer business questions in plain English with a SQL Plugin over a sample database. The
  built-in ``data_analyst`` LLMClient is a worked example.
- Build the same workflow as a single LLMClient and as an Orchestrator of several, and compare
  cost, latency and quality.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
