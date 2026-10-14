AI Application Development Master Class
=======================================

**Why Smarter.** Most AI application tutorials stop at a script that sends one prompt to the
OpenAI API and prints the answer. A real application has to do much more: keep the provider's
API key out of the browser, the logs and the repository; remember the conversation; let the LLM
call tools and then ask it again with their results; change the system prompt for each request
without saving the change; validate the JSON that comes back; stream progress to a chat window;
refuse what it must refuse; and run the same way on a laptop and in production. Smarter is a
production platform for LLM applications that does all of this, and its code is public. Its
`prompt handler
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/provider/services/text_completion/lib/openai_compatible_chat_provider.py>`__
speaks the OpenAI API to every provider. Its `built-in functions
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/prompt/functions>`__ are
tool calls with JSON Schema definitions. Its `plugins
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/base.py>`__
rewrite the system prompt when a prompt matches them. API keys are `encrypted Secrets
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/secret/models.py>`__ and
``SecretStr`` settings, and its `Proxy
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/proxy/services.py>`__ lets
any OpenAI SDK use a provider without ever seeing its key. The front end and the back end agree
on a `chat contract
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/contract/models.py>`__
written in Pydantic, published as JSON Schema, and compiled into the TypeScript types of
`Smarter Chat <https://github.com/smarter-sh/smarter-chat>`__, a React chat app built from the
open-source ``@chatscope/chat-ui-kit-react``, ``@chatscope/chat-ui-kit-styles`` and
``@microlink/react-json-view`` packages.

Each of these is a decision that a developer building an AI application will meet, and each is
taught here from code that runs in production, with its tests, its docstrings, the commits that
fixed its mistakes, and the :doc:`Architecture Decision Record </adr>` that explains it. Students
build a complete AI application of their own, module by module, in Docker, with Smarter beside
it as the reference implementation that they read, run and compare against.

**What the course covers.** Eighteen one-hour modules, each a 30-minute lecture and a 30-minute
lab, in six themes:

- **Foundations.** The full-stack MVC and MVT patterns, and where an LLM, a prompt handler and a
  chat window fit into them; the course's stack in Docker Compose; and fast reviews of the Python
  and the React that an AI application needs.
- **Talking to the LLM.** The ``openai`` package; Pydantic, and working with the JSON inside and
  outside the ``openai`` package, including JSON mode and structured outputs; and keeping API
  keys and other sensitive data secret.
- **The back end.** Django REST Framework for LLM APIs; an OpenAI-compatible prompt handler that
  any OpenAI SDK can call; and conversations and multi-step prompts, from message history and
  token budgets to orchestrating several LLM calls.
- **Making the LLM do things.** Tool calls and the tool call loop; mutating the system prompt for
  one request; and retrieval-augmented generation with the ``langchain`` packages.
- **The front end.** Streaming and progress events; a chat UI of the students' own, built from
  the ``@chatscope/chat-ui-kit-react``, ``@chatscope/chat-ui-kit-styles`` and
  ``@microlink/react-json-view`` npm packages; and a single-page chat web app built against a
  typed contract with its back end.
- **Production.** Guardrails, prompt injection and cost control; testing an AI application
  without calling a paid LLM; and shipping the whole stack in containers.

**Look at.**

- `smarter/smarter/apps/provider/services/text_completion/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/provider/services/text_completion>`__,
  the OpenAI-compatible prompt handler, with its tool call loop and system prompt.
- `smarter/smarter/apps/prompt/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/prompt>`__,
  the chat API, its Pydantic contract, its built-in tool functions and its progress stream.
- `smarter/smarter/apps/secret/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/secret>`__
  and `smarter/smarter/apps/proxy/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/proxy>`__,
  where API keys are kept and how callers use them without seeing them.
- `github.com/smarter-sh/smarter-chat <https://github.com/smarter-sh/smarter-chat>`__, the React
  chat app that Smarter's LLMClient workbench is built on, and a case study in composing a chat
  UI from open-source packages.

Each course plan lists every file that it uses, module by module, under *The Modules in the
Source Code*.

**Read.** :doc:`/smarter-framework/guides/openai-api-getting-started-guide`,
:doc:`/smarter-framework/guides/openai-json-examples`, :doc:`/smarter-framework/smarter-chat`,
:doc:`/smarter-resources/smarter-prompt`, :doc:`/smarter-resources/smarter-llmtool`,
:doc:`/smarter-resources/smarter-secret`, :doc:`/smarter-resources/smarter-proxy`,
:doc:`/smarter-resources/smarter-guardrail`, :doc:`ADR 008 </adr/008-function-calling>`,
:doc:`ADR 031 </adr/031-pydantic-over-json>`.

**Exercises.**

- Call the OpenAI API with the ``openai`` package, and parse the result into a Pydantic model
  that rejects anything it did not ask for.
- Move an API key from source code into a ``SecretStr`` setting read from the environment, and
  prove that it appears in no log, response or commit.
- Write a Django REST Framework endpoint that accepts an OpenAI chat completion request, and call
  it with the official OpenAI SDK by changing only its ``base_url``.
- Give the LLM a tool with a JSON Schema definition, run the tool call loop, and test it with a
  fake LLM.
- Add context to the system prompt of one request without saving it in the conversation's
  history.
- Build a chat window from ``@chatscope/chat-ui-kit-react``, with Markdown replies and a
  ``@microlink/react-json-view`` panel for each request, on a Vite page pointed at your own back
  end, and run the whole stack with ``docker compose up``.

**Course plans.** Two complete, ready-to-teach plans of 18 hours each, with a schedule, graded
assignments and rubrics, two capstone projects, recommended texts, further study and technical
prerequisites. This course is longer than the micro courses in this guide, and has formats of its
own, described in each plan. The grading scale and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`. Students new to building
web applications with an LLM can start with
:doc:`/smarter-instructors/example-courses/micro-courses/full-stack-development`, and students who
want to go deeper into Django afterwards can continue with the
:doc:`/smarter-instructors/example-courses/master-classes/django-master-class`.

.. toctree::
   :maxdepth: 1

   Three-day classroom course: 18 hours <ai-application-development/three-day>
   Six-week online course: 18 hours <ai-application-development/six-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
