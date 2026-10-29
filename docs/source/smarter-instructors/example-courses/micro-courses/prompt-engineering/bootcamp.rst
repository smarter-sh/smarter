Prompt Engineering: Classroom Bootcamp
======================================

An eight-hour classroom bootcamp in prompt engineering, for students who need no programming
experience. Students build, test and brand an AI assistant by editing a YAML manifest, and leave
with a working application that they designed for a real audience. Everything students build is a
Smarter :doc:`LLMClient </smarter-resources/smarter-llmclient>` manifest, the same YAML that runs in
production, and they start from the nineteen built-in LLMClients that ship with every installation:
the one-line `simple
<https://github.com/smarter-sh/example-manifests/blob/main/llm-clients/llmclient-simple.yaml>`__
assistant, and `customer_support
<https://github.com/smarter-sh/example-manifests/blob/main/llm-clients/llmclient-customer-support.yaml>`__,
a complete support agent with a persona, refusals, a skill, a tool and four guardrails. The prompt
engineering :doc:`workbench </smarter-framework/smarter-chat>` shows every request sent to the
model, every tool call and every plugin selected, beside the chat, so students see the effect of
each edit at once. See :doc:`../course-formats` for the standard bootcamp day, the grading scale and
the course policies, and :doc:`../prompt-engineering` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Anyone: business, communications, education, and the humanities as well as computing.
   * - **Deployment**
     - A shared Smarter instance run by the instructor. Students need only a web browser.
   * - **Models**
     - One small, inexpensive model as the default, and one model from a second provider for
       comparison.
   * - **Cost**
     - Expect less than $2 USD of model charges per student for the day, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain what a system prompt, a user prompt, temperature and a token limit each do.
2. Write a system prompt that gives an assistant a persona, a narrow job and clear refusals.
3. Test an assistant systematically with prompts that it should answer and prompts that it should
   decline, and record the results.
4. Compare the same prompts across temperatures and models, by quality, tokens and cost.
5. Give an assistant knowledge and tools with plugins, and explain when the model chooses to use
   them.

Technical Prerequisites
-----------------------

- **Required:** a laptop with a current web browser, and experience of using a chat assistant
  such as ChatGPT, Claude or Gemini.
- **Required:** reading and editing a YAML file: key-value pairs, indentation, lists and
  multi-line strings. Send students the `Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__ page beforehand. It takes 15 minutes.
- **Helpful:** a text editor such as `Visual Studio Code <https://code.visualstudio.com/>`__ with a
  YAML extension, for writing manifests outside the web console.
- **Not needed:** programming, Git or the command line.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: How a language model reads a prompt.** Tokens, next-token prediction, the
       context window, and the roles of the system and user messages. Tour of the Smarter web
       console and the prompt engineering :doc:`workbench </smarter-framework/smarter-chat>`, and
       its Console panel, which shows the exact request sent to the model.
   * - 2
     - 45
     - **Lab 1: Your first assistant.** Copy the built-in ``simple`` LLMClient's manifest, rename
       it, rewrite its ``spec.config.prompt.defaultSystemRole``, and apply it in the web console.
       Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Anatomy of a good system prompt.** Persona, audience, task, constraints, output
       format and refusals. Examples, delimiters and step-by-step instructions. Why positive
       instructions usually work better than prohibitions. Walk through the built-in
       `customer_support
       <https://github.com/smarter-sh/example-manifests/blob/main/llm-clients/llmclient-customer-support.yaml>`__
       LLMClient's system prompt line by line.
   * - 4
     - 45
     - **Lab 2: Test before you trust.** Write a test sheet of ten prompts that the assistant
       should answer and five that it should decline, run them, record the results, and revise
       the system prompt. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Settings and models.** ``defaultTemperature``, ``defaultMaxTokens``,
       ``provider`` and ``defaultModel``. What changes when a model is larger, newer or from
       another provider. How Smarter accounts for every token, and what a request costs.
   * - 6
     - 45
     - **Lecture 4: Knowledge and tools.** Why models make things up, and how to ground them.
       :doc:`Static </smarter-resources/llmtool/plugin/static>` and :doc:`Skill
       </smarter-resources/llmtool/plugin/skill>` plugins for knowledge; :doc:`Websearch
       </smarter-resources/llmtool/plugin/websearch>` and :doc:`API
       </smarter-resources/llmtool/plugin/api>` plugins for action. Two decisions decide whether a
       tool is used: Smarter offers a plugin only when the prompt matches one of its
       ``searchTerms``, and the model then calls it or not, guided by the plugin's description.
       Installed :doc:`Extensions </smarter-framework/extensibility>`, such as the weather tool,
       are offered on every prompt.
   * - 7
     - 45
     - **Lab 3: Experiments.** Run the test sheet at temperature 0 and 1, and on two models, and
       compare answers, tokens and cost. Then add one plugin and watch the tool calls in the
       Console. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: When prompts are not enough.** Prompt injection and jailbreaks, shown live.
       Why a rule in a system prompt is a request, while a
       :doc:`Guardrail </smarter-resources/smarter-guardrail>` is enforced. Adding the built-in
       ``off_topic_input`` and ``pii_redaction_input`` guardrails. Show it with "Lab 1: Talk to Sam"
       in the case study `Guardrails: Can You Trust the Model?
       <https://smarter.sh/case-studies/guardrails>`__: a keyword guardrail stops an injection and
       misses the same request respelled. Its first discussion question asks why a prompt obeyed 99
       times in 100 isn't good enough.
   * - 9
     - 45
     - **Lab 4: Break it, then fix it.** Swap assistants with a neighbor, try to make theirs go off
       topic or reveal its instructions, and report what worked. Fix your own with a better prompt
       or a guardrail. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Designing for a real audience.** Interviewing a client, writing example
       prompts and a welcome message, and branding the chat with
       :doc:`styles </smarter-resources/llmclient/styles>`. From sandbox to deployed: what
       ``smarter deploy`` does.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and a client, and sketch the assistant's
       job, audience and test plan with the instructor's feedback.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: A Focused Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students turn the general-purpose ``simple`` LLMClient into an assistant with one narrow job, such
as a campus library helper or a recipe adviser, with a name, a persona and a welcome message.

**Turn in:** the manifest (``.yaml``), and a screenshot of a short conversation in the workbench.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Manifest applies cleanly
     - 4
     - Valid YAML, unique name, applied without errors.
     - Applied only after the instructor's help, or with leftover fields from ``simple``.
   * - Persona and job
     - 6
     - System prompt states who the assistant is, who it serves and what it does, in plain
       language.
     - Persona is present, but the job is vague ("helps with anything about X").
   * - Boundaries
     - 6
     - States what the assistant must decline, and how it declines politely.
     - Boundaries are missing or contradict the job.
   * - Welcome and example prompts
     - 4
     - ``appWelcomeMessage`` and ``appExamplePrompts`` match the job and help a new user start.
     - Defaults left in place, or examples that the assistant cannot answer.

Assignment 2: Test Sheet and Revision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write fifteen test prompts (ten in scope, five out of scope), run them, mark each answer
as pass or fail against an expected behavior, revise the system prompt once, and run them again.

**Turn in:** a table of prompts, expected behavior and results before and after revision, and the
revised manifest.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Test coverage
     - 6
     - Prompts cover typical, unusual, ambiguous and adversarial requests.
     - Prompts are all variations of the same easy question.
   * - Expected behavior
     - 4
     - Each prompt has a specific, checkable expected behavior written before running it.
     - Expected behavior is missing, or written after seeing the answer.
   * - Revision
     - 6
     - The revision targets the observed failures, and the second run shows the effect.
     - The prompt was changed, but the change does not address the failures.
   * - Honest reporting
     - 4
     - Failures that remain are reported and explained.
     - Every result is marked as a pass, including ones that are not.

Assignment 3: Temperature, Model and Tool Experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run five prompts from their test sheet in three configurations (temperature 0, temperature
1, and a second model), then add one plugin and show a conversation in which the model calls it.

**Turn in:** a one-page comparison with a table of quality, tokens and cost for each configuration,
the plugin manifest, and a screenshot of the Console showing the tool call.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Controlled comparison
     - 5
     - Changes one setting at a time, with the same prompts in each run.
     - Several settings changed at once, so the results cannot be compared.
   * - Measurements
     - 5
     - Tokens and cost come from Smarter's records, and quality is scored against stated
       criteria.
     - Quality is a general impression, and tokens or cost are missing.
   * - Plugin works
     - 5
     - The model calls the plugin when it should, and the answer uses its result.
     - The plugin is applied but never called, and the student does not explain why.
   * - Recommendation
     - 5
     - Recommends a configuration for the assistant's job, with reasons drawn from the data.
     - No recommendation, or one that the data does not support.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: An Assistant for a Real Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Turn a real person's needs into a tested, branded AI assistant, and
justify its design.

Students interview a real client, such as a campus office, a student club or a local business, for
15 minutes, then build an LLMClient for them with at least one plugin, at least one guardrail and
custom styles.

**What students turn in:**

- The LLMClient, plugin and guardrail manifests, in a Git repository or a zip file.
- A one-page design brief: the client, the audience, the job, what the assistant must not do, and
  why the plugin and guardrail were chosen.
- A test sheet of at least twenty prompts with results.
- A five-minute recorded demonstration, or a live demonstration to the class.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fit to the client
     - 25
     - The brief shows the client's real needs, and the assistant meets them.
     - The client is named but the assistant is generic.
   * - System prompt quality
     - 20
     - Clear persona, task, constraints, format and refusals, with no contradictions.
     - Works for easy prompts, but breaks on ambiguous ones.
   * - Plugins and guardrails
     - 20
     - Each one is justified, configured correctly and shown working.
     - Present, but unused, misconfigured or unexplained.
   * - Testing
     - 20
     - Twenty or more varied prompts, with failures reported and addressed.
     - Few prompts, or only easy ones.
   * - Presentation and branding
     - 15
     - Styles, welcome message and examples suit the client. Demonstration is clear and on time.
     - Default appearance, or a demonstration that does not show the main features.

Capstone B: The Prompt Bake-off
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Use controlled experiments to choose between prompt designs and models,
and communicate the result with evidence.

Students pick one task, such as summarizing meeting notes, drafting customer replies or explaining
a concept to a twelve-year-old. They write three system prompts that use different techniques
(plain instructions, a persona with examples, step-by-step instructions), run all three on two
models against the same twelve inputs, and score every output with a rubric of their own design.

**What students turn in:**

- The six LLMClient manifests (three prompts on two models).
- The twelve inputs, the scoring rubric, and a spreadsheet of scores, tokens and cost.
- A two-page report that recommends one prompt and one model, with charts.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Experimental design
     - 25
     - Prompts differ in one technique each, inputs are representative, and runs are repeated.
     - Prompts differ in many ways at once, so no conclusion can be drawn.
   * - Scoring rubric
     - 20
     - Specific, observable criteria, applied consistently.
     - Vague criteria such as "good" or "helpful".
   * - Data
     - 20
     - Complete scores, tokens and cost for every run, from Smarter's records.
     - Missing runs, or estimated costs.
   * - Analysis
     - 20
     - Explains why the winning design worked, and where it still fails.
     - Reports the winner without explanation.
   * - Communication
     - 15
     - Clear charts, and a recommendation that a manager could act on.
     - Raw tables only, or a recommendation buried in the text.

Recommended Texts
-----------------

- **Pre-reading:** Ethan Mollick, *Co-Intelligence: Living and Working with AI* (Portfolio, 2024),
  chapters 1 to 3. A short, non-technical introduction to working with language models.
- **Reference:** John Berryman and Albert Ziegler, *Prompt Engineering for LLMs* (O'Reilly, 2024).
  Chapters 1 to 4 explain how a model sees a prompt, and are worth reading after the bootcamp.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-llmclient`,
  :doc:`/smarter-resources/smarter-llmtool`, :doc:`/smarter-resources/smarter-guardrail` and
  :doc:`/smarter-framework/smarter-manifests`.

Further Study
-------------

.. include:: further-study.txt
