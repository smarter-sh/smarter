Prompt Engineering: Two-Week Online Course
==========================================

A two-week online course in prompt engineering, for students who need no programming experience.
Students build, test and brand an AI assistant by editing a YAML manifest. Everything students build
is a Smarter :doc:`LLMClient </smarter-resources/smarter-llmclient>` manifest, the same YAML that
runs in production, and they start from the nineteen built-in LLMClients that ship with every
installation: the one-line `simple
<https://github.com/smarter-sh/example-manifests/blob/main/llm-clients/llmclient-simple.yaml>`__
assistant, and `customer_support
<https://github.com/smarter-sh/example-manifests/blob/main/llm-clients/llmclient-customer-support.yaml>`__,
a complete support agent with a persona, refusals, a skill, a tool and four guardrails. The prompt
engineering :doc:`workbench </smarter-framework/smarter-chat>` shows every request sent to the
model, every tool call and every plugin selected, beside the chat, so students see the effect of
each edit at once. There are six 30-minute recorded lectures and a 90-minute live session each week.
See :doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../prompt-engineering` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Anyone: business, communications, education, and the humanities as well as computing.
   * - **Deployment**
     - A shared Smarter instance run by the instructor. Students need only a web browser.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $5 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how a model turns a prompt into an answer, and what temperature and token limits do.
2. Write system prompts with a persona, a task, constraints, an output format and refusals.
3. Test an assistant systematically, and improve it from the evidence.
4. Choose a model and settings for a job by comparing quality, tokens and cost.
5. Ground an assistant with knowledge and tool plugins, and protect it with guardrails.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser and a reliable connection for video calls,
  and experience of using a chat assistant such as ChatGPT, Claude or Gemini.
- **Required:** basic YAML: key-value pairs, indentation, lists and multi-line strings. Lecture 1
  reviews it, and `Learn YAML in Y minutes <https://learnxinyminutes.com/docs/yaml/>`__ covers it.
- **Helpful:** `Visual Studio Code <https://code.visualstudio.com/>`__ with a YAML extension, and
  a GitHub account for submitting work.
- **Not needed:** programming or the command line.

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
     - **How a language model reads a prompt.** Tokens, next-token prediction, the context window,
       and system and user messages. A YAML refresher, and a tour of the web console and the
       prompt engineering :doc:`workbench </smarter-framework/smarter-chat>`.
   * - 1
     - Lecture 2 (30 min)
     - **Anatomy of a good system prompt.** Persona, audience, task, constraints, output format and
       refusals. Examples and delimiters. A line-by-line reading of the built-in
       ``customer_support`` LLMClient's system prompt.
   * - 1
     - Lecture 3 (30 min)
     - **Testing an assistant.** Writing test prompts with expected behavior, including edge cases
       and adversarial ones. Keeping a test sheet, and changing one thing at a time.
   * - 1
     - Live session 1 (90 min)
     - Live build of an assistant from the ``simple`` LLMClient, with questions. In pairs,
       students critique each other's system prompts with the checklist from Lecture 2. Start
       Assignment 1 together.
   * - 2
     - Lecture 4 (30 min)
     - **Settings, models and cost.** ``defaultTemperature``, ``defaultMaxTokens``, ``provider``
       and ``defaultModel``. Comparing models fairly. How Smarter records the tokens and cost of
       every request.
   * - 2
     - Lecture 5 (30 min)
     - **Knowledge and tools.** Grounding with :doc:`Static
       </smarter-resources/llmtool/plugin/static>` and :doc:`Skill
       </smarter-resources/llmtool/plugin/skill>` plugins, and acting with :doc:`Websearch
       </smarter-resources/llmtool/plugin/websearch>` and :doc:`API
       </smarter-resources/llmtool/plugin/api>` plugins. Smarter offers a plugin only when the prompt
       matches one of its ``searchTerms``, and the model then decides, from the plugin's
       description, whether to call it. Installed :doc:`Extensions
       </smarter-framework/extensibility>`, such as the weather tool, are offered on every prompt.
   * - 2
     - Lecture 6 (30 min)
     - **When prompts are not enough.** Prompt injection and jailbreaks. Why a
       :doc:`Guardrail </smarter-resources/smarter-guardrail>` is enforced while a system prompt
       is only a request. Branding with :doc:`styles </smarter-resources/llmclient/styles>`, and
       deploying an assistant. Show it with "Lab 1: Talk to Sam" in the case study `Guardrails: Can
       You Trust the Model? <https://smarter.sh/case-studies/guardrails>`__: a keyword guardrail
       stops an injection and misses the same request respelled. Its first discussion question asks
       why a prompt obeyed 99 times in 100 isn't good enough.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions), then a
       class discussion of what worked across projects.

Assignments 1 and 2 are due before Live session 2. Assignment 3 and the capstone are due at the
start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: A Focused Assistant with a Test Sheet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students turn the general-purpose ``simple`` LLMClient into an assistant with one narrow job, and
test it with fifteen prompts: ten that it should answer and five that it should decline.

**Turn in:** the manifest, and the test sheet with expected behavior and results.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Manifest
     - 4
     - Valid, applies cleanly, unique name, sensible welcome message and example prompts.
     - Applies only with help, or keeps defaults from ``simple``.
   * - System prompt
     - 6
     - Clear persona, audience, job and refusals.
     - Persona present, but the job or the refusals are vague.
   * - Test sheet
     - 6
     - Varied prompts, each with a checkable expected behavior written in advance.
     - Easy prompts only, or expected behavior written after the fact.
   * - Reporting
     - 4
     - Results are honest, and failures are explained.
     - Every result is a pass, including ones that are not.

Assignment 2: Revise from Evidence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students revise their system prompt twice, each time to fix failures from the test sheet, and
re-run every test after each revision. A short note explains each change and its effect.

**Turn in:** the three versions of the manifest (or a Git history with three commits), the updated
test sheet, and a one-page change log.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Targeted changes
     - 6
     - Each revision addresses specific, observed failures.
     - Changes are general rewrites unconnected to the test results.
   * - Regression checking
     - 5
     - All tests are re-run after each revision, and regressions are noted.
     - Only the failing tests are re-run.
   * - Technique
     - 5
     - Uses at least two techniques from the lectures, such as examples, delimiters or an output
       format.
     - Only adds more instructions.
   * - Change log
     - 4
     - Concise and specific: what changed, why, and what happened.
     - Missing, or a list of changes without reasons.

Assignment 3: Model, Settings and Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run five of their test prompts at temperature 0 and 1 and on a second model, then add a
plugin and a guardrail, and show each one working.

**Turn in:** a comparison table of quality, tokens and cost, the plugin and guardrail manifests,
Console screenshots of a tool call and of a guardrail intervention, and a recommendation of one
paragraph.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Controlled comparison
     - 5
     - One setting changed at a time, same prompts, figures from Smarter's records.
     - Several settings changed at once, or estimated figures.
   * - Plugin
     - 5
     - Called when it should be, and its result is used in the answer.
     - Applied but never called, without explanation.
   * - Guardrail
     - 5
     - Blocks or redacts what it should, and lets normal prompts through.
     - Blocks normal prompts too, or never triggers.
   * - Recommendation
     - 5
     - A configuration chosen for the assistant's job, with reasons from the data.
     - Missing, or unsupported by the data.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: An Assistant for a Real Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Turn a real person's needs into a tested, branded and governed AI
assistant, and justify its design.

Students interview a real client, such as a campus office, a club, a nonprofit or a local
business, and build an LLMClient for them with at least one knowledge plugin, one tool plugin, two
guardrails and custom styles.

**What students turn in:**

- A Git repository with every manifest, and a ``README.md`` that explains how to apply them.
- A two-page design brief: the client, the audience, the job, the risks, and the reason for each
  plugin and guardrail.
- A test sheet of at least twenty-five prompts, with results from the final version.
- A five-minute presentation with a live demonstration.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fit to the client
     - 20
     - The brief reflects a real interview, and the assistant meets the client's needs.
     - The client is named, but the assistant is generic.
   * - System prompt
     - 20
     - Clear, consistent and robust to ambiguous and adversarial prompts.
     - Works for easy prompts only.
   * - Plugins and guardrails
     - 25
     - Each is justified, configured correctly and shown working.
     - Present but unused, misconfigured or unexplained.
   * - Testing
     - 20
     - Varied tests, honest results, and failures addressed or explained.
     - Few or easy tests, or results that do not match the demonstration.
   * - Presentation
     - 15
     - Clear, on time, and shows the design decisions as well as the result.
     - Overruns, or shows the chat without explaining the design.

Capstone B: A Prompt Pattern Library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Generalize from individual prompts to reusable patterns, and demonstrate
with evidence when each pattern helps.

Students build a small library of five prompt patterns, for example *persona with refusals*,
*few-shot examples*, *structured output*, *step-by-step reasoning* and *grounded answer with
citations*. For each pattern they build a before-and-after pair of LLMClients that differ only in
that pattern, and measure the difference on ten inputs.

**What students turn in:**

- A Git repository with the ten LLMClient manifests and the inputs.
- For each pattern, a one-page card: what it is, when to use it, a template, the measured
  effect, and a known failure.
- A five-minute presentation of the most surprising result.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Pattern selection
     - 15
     - Five distinct patterns, each useful in practice.
     - Patterns overlap, or two are the same idea.
   * - Controlled pairs
     - 25
     - Each pair differs only in the pattern, and is tested on the same inputs.
     - Pairs differ in several ways.
   * - Evidence
     - 25
     - Measured effect on quality, tokens and cost, with scoring criteria stated.
     - Claims without measurements.
   * - Pattern cards
     - 20
     - Templates are reusable, and failures are honest.
     - Cards describe the example rather than the pattern.
   * - Presentation
     - 15
     - Clear, on time, and teaches classmates something new.
     - Overruns, or reads the cards aloud.

Recommended Texts
-----------------

- **Required:** John Berryman and Albert Ziegler, *Prompt Engineering for LLMs* (O'Reilly, 2024).
  Week 1: chapters 1 to 4. Week 2: chapters 5 to 8.
- **Background:** Ethan Mollick, *Co-Intelligence: Living and Working with AI* (Portfolio, 2024).
- **Smarter documentation:** :doc:`/smarter-resources/smarter-llmclient`,
  :doc:`/smarter-resources/smarter-llmtool`, :doc:`/smarter-resources/smarter-guardrail`,
  :doc:`/smarter-resources/llmclient/styles` and :doc:`/smarter-framework/smarter-manifests`.

Further Study
-------------

.. include:: further-study.txt
