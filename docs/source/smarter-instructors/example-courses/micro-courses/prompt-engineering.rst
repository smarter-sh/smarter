Prompt Engineering
==================

**Why Smarter.** Most prompt engineering courses are taught in a consumer chat app, where students
can change only the words they type. In Smarter, students change everything that shapes a model's
behavior, by editing a short YAML manifest and with no code: the system prompt, the provider, the
model, the temperature and the token limit, the knowledge and tools the model may use, the
guardrails around it, and how its chat looks. Every one of those settings is defined, with a
description, in a `Pydantic model
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/manifest/models/llmclient/spec.py>`__,
so a misspelled key is an error that says why, not a silent no-op.

Students see the result straight away in the prompt engineering
:doc:`workbench </smarter-framework/smarter-chat>`, whose `Console
<https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter-workbench/src/components/Console>`__
shows, beside the chat, the configuration, every request sent to the model, every tool call,
which plugins were selected, and the server's logs. The same prompt can be tried against several
providers and models by changing two lines, and Smarter records the tokens and the
:doc:`cost </smarter-platform/cost-accounting>` of every request, so a comparison is measured, not
guessed.

Students start from real examples, not toy ones. Every installation ships with
`nineteen built-in LLMClients <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmclient/data/llm-clients>`__,
from the one-line `simple
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/data/llm-clients/llmclient-simple.yaml>`__
assistant to `customer_support
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/data/llm-clients/llmclient-customer-support.yaml>`__,
a complete support agent with a persona, refusals, a skill, a tool and four guardrails; twenty
`sample plugins <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/data/sample-plugins>`__;
and eighteen `built-in guardrails
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__.
Smarter also makes visible a point that most courses miss: a tool is used only after two
decisions. Smarter :doc:`selects a plugin </smarter-resources/llmtool/nlp>` when the prompt matches
one of its search terms, exactly, with a typo or as a synonym, and only then does the model decide,
from the plugin's description, whether to call it. Installed
:doc:`Extensions </smarter-framework/extensibility>`, such as the weather tool, skip the first
decision: an LLMClient that lists one offers its tools on every prompt.

**What the course covers.** How a language model reads a prompt: tokens, the context window, and
system and user messages; the anatomy of a good system prompt, from persona to refusals; few-shot
examples, delimiters and structured output; testing an assistant systematically, and scoring
answers with a rubric and an LLM-as-judge; temperature, token limits, models and cost; grounding
with Static and Skill plugins and with retrieval from a Vectorstore; tools, and how plugin
selection works; prompt injection, jailbreaks and guardrails; multi-step workflows with an
Orchestrator; and designing, branding and deploying an assistant for a real audience.

**Look at.**

- `llmclient/data/llm-clients/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmclient/data/llm-clients>`__,
  the built-in LLMClients, especially ``simple``, ``customer_support`` and ``weather``.
- `llmtool/data/sample-plugins/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/data/sample-plugins>`__,
  the sample Static, Skill, Websearch and ImageSearch plugins.
- `guardrail/data/guardrails/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__,
  the built-in guardrails, each a short manifest that a non-programmer can read.

Each course plan lists every manifest and file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-resources/smarter-llmclient`, :doc:`/smarter-resources/smarter-llmtool`,
:doc:`/smarter-resources/llmtool/nlp`, :doc:`/smarter-resources/llmclient/styles`,
:doc:`/smarter-resources/smarter-guardrail`, :doc:`/smarter-framework/smarter-manifests`.

**Exercises.**

- Start from the built-in ``simple`` LLMClient. Rewrite its ``spec.config.prompt.defaultSystemRole``
  to give it a persona and a narrow job, then write test prompts that it should answer and prompts
  that it should decline.
- Run the same ten prompts at ``defaultTemperature`` 0 and 1, and on two models. Compare the
  answers, the tokens used and the cost.
- Give an LLMClient knowledge with a :doc:`SkillPlugin </smarter-resources/llmtool/plugin/skill>` or
  a :doc:`Static Plugin </smarter-resources/llmtool/plugin/static>`, and the ability to act with a
  :doc:`Websearch Plugin </smarter-resources/llmtool/plugin/websearch>` or an
  :doc:`API Plugin </smarter-resources/llmtool/plugin/api>`. Use the Console to see when Smarter
  selects the plugin and when the model calls it, and how the search terms and the description
  each influence that.
- Try to make an assistant go off topic, then add the built-in ``off_topic_input`` guardrail and
  try again.
- Design an application for a real client (a campus office, a club, a local business), brand its
  chat with ``spec.config.styles``, and present it.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <prompt-engineering/bootcamp>
   Two-week online course: 6 hours <prompt-engineering/two-week>
   Four-week online course: 12 hours <prompt-engineering/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
