AI Application Development Master Class: Three-Day Classroom Course
===================================================================

A three-day classroom master class for experienced developers who want to build complete,
full-stack AI applications with Docker, Python, Django, React and the OpenAI API. Over 18 hours,
students build one application of their own, module by module, while they read how a production
platform for LLM applications solves each problem: the ``openai`` and ``langchain`` packages,
Pydantic and JSON, API keys kept secret, Django REST Framework, an OpenAI-compatible prompt
handler, conversations and multi-step prompts, tool calls, a system prompt changed for each
request, retrieval, streaming, a chat UI of their own built from open-source React components, a
single-page chat app, guardrails, testing without a paid LLM, and shipping it all in containers. Each topic is a
one-hour module, a 30-minute lecture and a 30-minute lab. Day 1 covers the foundations and
talking to the LLM, day 2 the back end and making the LLM do things, and day 3 the front end and
production. See :doc:`/smarter-instructors/example-courses/micro-courses/course-formats` for the
grading scale and the course policies, and :doc:`../ai-application-development` for an overview
of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Professional developers who build web applications and want to build AI applications:
       back-end, front-end and full-stack engineers, and technical leads.
   * - **Format**
     - Three days of six hours of instruction, each day six one-hour modules. Breaks and lunch are
       not counted.
   * - **Deployment**
     - On each student's laptop, under Docker Compose, working before day 1: Smarter from source,
       for reading and comparing, and the course app, which students start in Module 1.
   * - **Models**
     - An OpenAI model for chat and tool calls, and an OpenAI embedding model for retrieval.
       Smarter's LLMClients use the same key.
   * - **Workload**
     - About 2 hours each evening for the day's assignment, and 10 to 15 hours for the capstone in
       the week after the course.
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
  with the `official tutorial <https://docs.python.org/3/tutorial/>`__ before day 1.
- **Required:** building complete web sites with HTML, CSS and JavaScript, and familiarity with a
  JavaScript framework, such as React, Vue or Angular.
- **Required:** proficiency with REST APIs and JSON: methods, status codes, headers and
  authentication, with ``curl`` or a client such as Postman.
- **Required:** working in a terminal with common Linux commands, and Git and GitHub: clone,
  branch, commit, push and pull requests.
- **Required:** the basics of relational databases and SQL.
- **Required before day 1:** Docker Desktop or Docker Engine with Compose, Node.js LTS, Python
  3.12 or later, a code editor, at least 16 GB of memory, and Smarter running from source as
  described in :doc:`/smarter-framework/guides/developer-setup`. Send students the instructions
  at least a week ahead, and ask for a screenshot of the running web console.
- **Required before day 1:** an OpenAI API key with credit, set in Smarter's ``.env``, and a
  prompt answered in Smarter's LLMClient workbench.
- **Helpful:** reading TypeScript, Django, and the Model-View-Controller pattern. Students new to
  Docker can take :doc:`/smarter-instructors/example-courses/micro-courses/docker` first.
- **Not needed:** machine learning, statistics or experience with LLMs beyond using a chat
  assistant.

Schedule
--------

Each module is described under `The Modules`_.

.. list-table::
   :header-rows: 1
   :widths: 10 30 30 30

   * - Day
     - Morning (3 hours)
     - Afternoon (3 hours)
     - Evening
   * - 1
     - Modules 1 to 3: the full-stack AI application; Python for AI applications; React for AI
       applications.
     - Modules 4 to 6: the openai package; Pydantic and JSON; keeping secrets secret.
     - Assignment 1, due at the start of day 2.
   * - 2
     - Modules 7 to 9: Django REST Framework for LLM APIs; an OpenAI-compatible prompt handler;
       conversations and multi-step prompts.
     - Modules 10 to 12: tool calls; mutating the system prompt; retrieval with LangChain.
     - Assignment 2, due at the start of day 3.
   * - 3
     - Modules 13 to 15: streaming and progress; building a chat UI with chatscope; a single-page
       chat web app.
     - Modules 16 to 18: guardrails, prompt injection and cost; testing AI applications;
       shipping the whole stack.
     - Assignment 3, due two days after the course. Capstone choice.

Each day opens with 10 minutes of questions on the previous evening's assignment, taken from the
first lecture's time. The capstone is due one week after the course.

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
     - 45% (3 × 15%)
   * - Participation (labs and questions)
     - 10%
   * - Capstone project
     - 45%

The grading scale, the rubric levels and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`.

Graded Assignments
------------------

Each assignment builds on the day's labs, in the student's course app repository, and is
submitted as a pull request against their own repository.

Assignment 1: A Typed, Secret-Safe LLM Call
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

Assignment 2: A Prompt Handler with Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish the course app's OpenAI-compatible endpoint: history trimmed to a token budget,
two tools in a working tool call loop, and a system prompt changed for each request but never
saved. They call it from a script with the official ``openai`` package, changing only
``base_url`` and ``api_key``.

**Turn in:** the pull request, with tests, and the script.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Compatibility
     - 5
     - The official SDK works against it unchanged.
     - A custom request shape.
   * - Tool call loop
     - 7
     - Every call answered by a paired ``tool`` message, arguments validated, then asked again.
     - One tool call, or arguments trusted.
   * - System prompt and history
     - 5
     - Mutated copy sent, saved history unchanged, with a test that proves it.
     - The mutation saved into history.
   * - Tests
     - 3
     - The loop tested with recorded responses.
     - None.

Assignment 3: The Single-Page Chat App
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students put a React single-page app of their own in front of the Assignment 2 endpoint, built
from ``@chatscope/chat-ui-kit-react`` with a ``@microlink/react-json-view`` panel that shows each
request and tool call, TypeScript types generated from the back end's JSON Schema, streamed
progress, and an input guardrail on the back end. The whole stack runs with
``docker compose up`` from a clean clone.

**Turn in:** the pull request, and a two-minute screen recording from ``docker compose up`` to a
streamed reply.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Contract
     - 5
     - Generated types, with a test that fails when the back end changes.
     - Hand-written types.
   * - Streaming
     - 5
     - Progress and reply streamed, errors shown in the thread.
     - The page waits for the whole reply.
   * - Guardrail
     - 4
     - Blocks a secret in a prompt, with a clear message, and logs it without the secret.
     - Logs the secret it blocked.
   * - Shipping
     - 6
     - Runs from a clean clone, with no key in the image or the bundle.
     - Needs manual steps, or ships the key to the browser.

Capstone Projects
-----------------

Students choose one at the end of day 3, and submit it one week after the course.

.. include:: capstones.txt

Recommended Texts
-----------------

- **Pre-reading:** :doc:`/smarter-framework/guides/openai-api-getting-started-guide` and
  :doc:`/smarter-framework/guides/openai-json-examples`, before day 1.
- **Required:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025), the chapters on prompt engineering, retrieval and agents, and evaluation,
  before and during the course.
- **Reference:** John Berryman and Albert Ziegler, *Prompt Engineering for LLMs* (O'Reilly,
  2024), for system prompts, context and tools.
- **Reference:** Mayo Oshin and Nuno Campos, *Learning LangChain* (O'Reilly, 2025), for
  retrieval and multi-step workflows.
- **Reference:** Luciano Ramalho, *Fluent Python*, 2nd edition (O'Reilly, 2022), and Alex Banks
  and Eve Porcello, *Learning React*, 2nd edition (O'Reilly, 2020), for the reviews on day 1.
- **Reference:** William S. Vincent, *Django for APIs* (latest edition), for Django REST
  Framework.
- **In the repository:** :doc:`/adr`, :doc:`/smarter-framework/smarter-chat`,
  :doc:`/smarter-resources/smarter-prompt`, :doc:`/smarter-resources/smarter-plugin`,
  :doc:`/smarter-resources/smarter-proxy` and :doc:`/smarter-resources/smarter-guardrail`.

Further Study
-------------

.. include:: further-study.txt
