AI Application Development Master Class: Six-Week Online Course
===============================================================

A six-week online master class for experienced developers who want to build complete,
full-stack AI applications with Docker, Python, Django, React and the OpenAI API. Over 18 hours,
students build one application of their own, module by module, while they read how a production
platform for LLM applications solves each problem: the ``openai`` and ``langchain`` packages,
Pydantic and JSON, API keys kept secret, Django REST Framework, an OpenAI-compatible prompt
handler, conversations and multi-step prompts, tool calls, a system prompt changed for each
request, retrieval, streaming, a chat UI of their own built from open-source React components, a
single-page chat app, guardrails, testing without a paid LLM, and shipping it all in containers. Each topic is a
one-hour module: a 30-minute recorded lecture, and a lab done together in the week's live
session. Week 1 covers the foundations, week 2 talking to the LLM, week 3 the back end, week 4
making the LLM do things, week 5 the front end, and week 6 production. See
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats` for the grading scale and
the course policies, and :doc:`../ai-application-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Professional developers who build web applications and want to build AI applications:
       back-end, front-end and full-stack engineers, and technical leads.
   * - **Format**
     - Each week, three 30-minute recorded lectures (1 hour 30) and one 90-minute live session for
       the week's three labs: 3 hours of instruction a week, 18 in all.
   * - **Deployment**
     - On each student's computer, under Docker Compose, working before the first live session:
       Smarter from source, for reading and comparing, and the course app, which students start
       in Module 1.
   * - **Models**
     - An OpenAI model for chat and tool calls, and an OpenAI embedding model for retrieval.
       Smarter's LLMClients use the same key.
   * - **Workload**
     - 3 hours of instruction and 3 to 5 hours of assignments each week, and 10 to 15 hours for
       the capstone, in week 6 and the week after.
   * - **Cost**
     - Free software, plus an OpenAI API key with a few dollars of credit: about $5 to $10 per
       student for the course and the capstone. Cap each student's spending with a
       :doc:`Budget </smarter-resources/smarter-budget>` on a shared Smarter Provider, or with a
       project budget in the OpenAI dashboard.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the architecture of a full-stack AI application in MVC and MVT terms, and place its
   LLM, prompt handler and chat window in it.
2. Call LLMs with the ``openai`` package, validate their JSON with Pydantic, and use the
   ``langchain`` packages for embeddings and retrieval.
3. Keep API keys and other sensitive data out of source code, Git history, logs, images and
   browsers.
4. Build an OpenAI-compatible prompt API with Django REST Framework that handles conversation
   history, multi-step prompts and tool calls.
5. Shape an LLM's behavior for each request by mutating the system prompt, adding retrieved
   context and applying guardrails, and defend the application against prompt injection.
6. Build a single-page React chat app of their own from ``@chatscope/chat-ui-kit-react`` and
   ``@microlink/react-json-view``, against a typed contract with the back end, with streamed
   progress.
7. Test an AI application without calling a paid LLM, and run the whole stack with Docker
   Compose.

Technical Prerequisites
-----------------------

- **Required:** professional experience with at least one programming language, such as Python,
  Visual Basic, C, Rust or Go. Students who know another language well can catch up on Python
  with the `official tutorial <https://docs.python.org/3/tutorial/>`__ in week 1.
- **Required:** building complete web sites with HTML, CSS and JavaScript, and familiarity with a
  JavaScript framework, such as React, Vue or Angular.
- **Required:** proficiency with REST APIs and JSON: methods, status codes, headers and
  authentication, with ``curl`` or a client such as Postman.
- **Required:** working in a terminal with common Linux commands, and Git and GitHub: clone,
  branch, commit, push and pull requests.
- **Required:** the basics of relational databases and SQL.
- **Required by the first live session:** Docker Desktop or Docker Engine with Compose, Node.js
  LTS, Python 3.12 or later, a code editor, at least 16 GB of memory, and Smarter running from
  source as described in :doc:`/smarter-framework/guides/developer-setup`.
- **Required by the first live session:** an OpenAI API key with credit, set in Smarter's
  ``.env``, and a prompt answered in Smarter's LLMClient workbench.
- **Helpful:** reading TypeScript, Django, and the Model-View-Controller pattern. Students new to
  Docker can take :doc:`/smarter-instructors/example-courses/micro-courses/docker` first.
- **Not needed:** machine learning, statistics or experience with LLMs beyond using a chat
  assistant.

Schedule
--------

Students watch the week's three lectures before its live session. Each module is described under
`The Modules`_.

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - Week
     - Lectures
     - Assignment
   * - 1
     - Modules 1 to 3: the full-stack AI application; Python for AI applications; React for AI
       applications.
     - Assignment 1: The Course App, Running.
   * - 2
     - Modules 4 to 6: the openai package; Pydantic and JSON; keeping secrets secret.
     - Assignment 2: A Typed, Secret-Safe LLM Call.
   * - 3
     - Modules 7 to 9: Django REST Framework for LLM APIs; an OpenAI-compatible prompt handler;
       conversations and multi-step prompts.
     - Assignment 3: An OpenAI-Compatible Endpoint.
   * - 4
     - Modules 10 to 12: tool calls; mutating the system prompt; retrieval with LangChain.
     - Assignment 4: Tools, Context and Retrieval.
   * - 5
     - Modules 13 to 15: streaming and progress; building a chat UI with chatscope; a single-page
       chat web app.
     - Assignment 5: The Single-Page Chat App. Capstone choice.
   * - 6
     - Modules 16 to 18: guardrails, prompt injection and cost; testing AI applications;
       shipping the whole stack.
     - Capstone, due one week after the last live session.

Live Sessions
~~~~~~~~~~~~~

This course's live sessions differ from the standard session in
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`, because they hold the
labs:

- **15 minutes:** questions on the week's lectures, and common problems seen in the previous
  week's assignment.
- **75 minutes:** the week's three labs, 25 minutes each. The instructor demonstrates the start
  of each lab, then students work in pairs in breakout rooms, sharing one screen.

Students finish any lab that runs over on their own, before starting the week's assignment.
Assignments are due before the next live session.

The Modules
-----------

.. include:: modules.txt

The Modules in the Source Code
------------------------------

.. include:: source-code.txt

Grading
-------

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Component
     - Weight
   * - Graded assignments
     - 50% (5 × 10%)
   * - Participation (live sessions and labs)
     - 10%
   * - Capstone project
     - 40%

The grading scale, the rubric levels and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`.

Graded Assignments
------------------

Each assignment builds on the week's labs, in the student's course app repository, and is
submitted as a pull request against their own repository.

Assignment 1: The Course App, Running
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish the course app's skeleton: a Django project and a Vite React app in one Compose
file with Redis, the Module 2 function with tests, and the Module 3 chat page talking to an echo
endpoint. A one-page note traces one chat message through Smarter, from the chat window to the
provider and back, naming the file of each step.

**Turn in:** the pull request, and the one-page trace.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Stack
     - 6
     - ``docker compose up`` starts all three services from a clean clone.
     - Needs manual steps.
   * - Python and React
     - 6
     - A typed, tested function, and a chat page with loading and error states.
     - Untyped, or no error state.
   * - Trace
     - 8
     - Every step, in order, with the file, checked against the workbench's Console.
     - Guessed from file names.

Assignment 2: A Typed, Secret-Safe LLM Call
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish the Module 5 classifier as a Django service function that returns a Pydantic
model, with the API key in a ``SecretStr`` setting, and the SDK's errors turned into clear
messages. A paragraph compares their key handling with Smarter's ``settings.py`` and
``secret/models.py``, and says what commit 990cab95b would have caught in their own code.

**Turn in:** the pull request, with tests that use a fake client, and the paragraph.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Structured output
     - 6
     - Validated into a strict model, with invalid output handled.
     - ``json.loads()`` and hope.
   * - Secrets
     - 6
     - ``SecretStr`` from the environment, masked in logs, absent from Git history.
     - Key in source, or printed in a log.
   * - Errors
     - 4
     - Rate limits, bad keys and timeouts each give a clear message.
     - A stack trace.
   * - Tests
     - 4
     - A fake client; no network.
     - Tests that call the paid API.

Assignment 3: An OpenAI-Compatible Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish the course app's ``/v1/chat/completions`` endpoint in Django REST Framework,
authenticated by API key, with conversations stored in a model and trimmed to a token budget,
and a two-step prompt that drafts a reply and then checks it. They call it from a script with the
official ``openai`` package, changing only ``base_url`` and ``api_key``.

**Turn in:** the pull request, with tests, and the script.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Compatibility
     - 6
     - The official SDK works against it unchanged, errors included.
     - A custom request shape.
   * - History
     - 6
     - Stored, sent, and trimmed by counted tokens.
     - Trimmed by message count, or not at all.
   * - Multi-step prompt
     - 4
     - Two requests, the second checking the first, both logged.
     - One request that asks for both.
   * - Tests
     - 4
     - Authentication refused and accepted, with a fake LLM.
     - None.

Assignment 4: Tools, Context and Retrieval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add two tools in a working tool call loop, a system prompt changed for each request but
never saved, and retrieval over a folder of documents with LangChain, with sources cited in the
reply.

**Turn in:** the pull request, with tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Tool call loop
     - 8
     - Every call answered by a paired ``tool`` message, arguments validated, then asked again.
     - One tool call, or arguments trusted.
   * - System prompt and history
     - 6
     - Mutated copy sent, saved history unchanged, with a test that proves it.
     - The mutation saved into history.
   * - Retrieval
     - 6
     - Split, embedded and retrieved, with cited sources.
     - Whole documents pasted into the prompt.

Assignment 5: The Single-Page Chat App
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students put a React single-page app of their own in front of the course app's endpoint, built
from ``@chatscope/chat-ui-kit-react`` with a ``@microlink/react-json-view`` panel that shows each
request and tool call, TypeScript types generated from the back end's JSON Schema, and streamed
progress for each LLM request and tool call.

**Turn in:** the pull request, and a two-minute screen recording of a streamed reply that uses a
tool.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Contract
     - 7
     - Generated types, with a test that fails when the back end changes.
     - Hand-written types.
   * - Streaming
     - 7
     - Progress and reply streamed, errors shown in the thread.
     - The page waits for the whole reply.
   * - Rendering
     - 6
     - Markdown rendered and sanitized; no key in the bundle.
     - Raw HTML from the LLM inserted into the page.

Capstone Projects
-----------------

Students choose one in week 5, work on it in week 6, and submit it one week after the last live
session.

.. include:: capstones.txt

Recommended Texts
-----------------

- **Pre-reading:** :doc:`/smarter-framework/guides/openai-api-getting-started-guide` and
  :doc:`/smarter-framework/guides/openai-json-examples`, before week 2.
- **Required:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025): prompt engineering in week 2, retrieval and agents in week 4, and evaluation
  in week 6.
- **Reference:** John Berryman and Albert Ziegler, *Prompt Engineering for LLMs* (O'Reilly,
  2024), for system prompts, context and tools.
- **Reference:** Mayo Oshin and Nuno Campos, *Learning LangChain* (O'Reilly, 2025), for
  retrieval and multi-step workflows.
- **Reference:** Luciano Ramalho, *Fluent Python*, 2nd edition (O'Reilly, 2022), and Alex Banks
  and Eve Porcello, *Learning React*, 2nd edition (O'Reilly, 2020), for the reviews in week 1.
- **Reference:** William S. Vincent, *Django for APIs* (latest edition), for Django REST
  Framework.
- **In the repository:** :doc:`/adr`, :doc:`/smarter-framework/smarter-chat`,
  :doc:`/smarter-resources/smarter-prompt`, :doc:`/smarter-resources/smarter-plugin`,
  :doc:`/smarter-resources/smarter-proxy` and :doc:`/smarter-resources/smarter-guardrail`.

Further Study
-------------

.. include:: further-study.txt
