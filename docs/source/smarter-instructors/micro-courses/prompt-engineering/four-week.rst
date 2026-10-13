Prompt Engineering: Four-Week Online Course
===========================================

A four-week online course in prompt engineering, for students who need no programming experience.
Students build, evaluate and brand an AI assistant by editing a YAML manifest. Everything students
build is a Smarter :doc:`LLMClient </smarter-resources/smarter-llmclient>` manifest, the same YAML
that runs in production, and they start from the nineteen built-in LLMClients that ship with every
installation: the one-line `simple
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/data/llm-clients/llmclient-simple.yaml>`__
assistant, and `customer_support
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/data/llm-clients/llmclient-customer-support.yaml>`__,
a complete support agent with a persona, refusals, a skill, a tool and four guardrails. The prompt
engineering :doc:`workbench </smarter-framework/smarter-chat>` shows every request sent to the
model, every tool call and every plugin selected, beside the chat, so students see the effect of
each edit at once. There are twelve 30-minute recorded lectures and a 90-minute live session each
week. The extra time, compared with the two-week course, goes to evaluation, retrieval and
multi-step workflows. See :doc:`../course-formats` for the format, the grading scale and the course
policies, and :doc:`../prompt-engineering` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Anyone: business, communications, education, and the humanities as well as computing.
   * - **Deployment**
     - A shared Smarter instance run by the instructor. Students need only a web browser.
       Students who want to may install their own with the
       :doc:`Quick Start </smarter-platform/installation/quick-start>` in week 3.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $10 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how a model turns a prompt into an answer, including tokens, context, sampling and
   tool calls.
2. Write and maintain system prompts with a persona, a task, constraints, an output format and
   refusals.
3. Evaluate an assistant with a test set and a scoring rubric, including an LLM-as-judge, and
   improve it from the evidence.
4. Choose a model and settings by comparing quality, latency, tokens and cost.
5. Ground an assistant with knowledge, retrieval and tool plugins, and protect it with guardrails.
6. Design, document and present an AI assistant for a real audience.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser and a reliable connection for video calls,
  and experience of using a chat assistant such as ChatGPT, Claude or Gemini.
- **Required:** basic YAML: key-value pairs, indentation, lists and multi-line strings. Lecture 1
  reviews it, and `Learn YAML in Y minutes <https://learnxinyminutes.com/docs/yaml/>`__ covers it.
- **Required by week 2:** a GitHub account, and enough Git to commit and push a file through the
  GitHub web interface or `GitHub Desktop <https://desktop.github.com/>`__.
- **Helpful:** `Visual Studio Code <https://code.visualstudio.com/>`__ with a YAML extension, a
  spreadsheet program, and reading JSON.
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
     - Lecture 1
     - **How a language model reads a prompt.** Tokens, next-token prediction, the context window,
       and system and user messages. A YAML refresher, and a tour of the web console and the
       :doc:`workbench </smarter-framework/smarter-chat>`.
   * - 1
     - Lecture 2
     - **Anatomy of a good system prompt.** Persona, audience, task, constraints, output format and
       refusals. A line-by-line reading of the built-in ``customer_support`` LLMClient.
   * - 1
     - Lecture 3
     - **Techniques.** Examples (few-shot prompting), delimiters, step-by-step instructions, and
       asking for structured output. When each helps, and when it only costs tokens.
   * - 1
     - Live session 1
     - Live build of an assistant from the ``simple`` LLMClient. Pairs critique each other's system
       prompts. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Testing an assistant.** Test sets with expected behavior, edge cases, adversarial prompts,
       and regression testing after every change.
   * - 2
     - Lecture 5
     - **Scoring answers.** Writing a rubric, scoring by hand, and using a second model as a judge.
       How judges are biased, and how to check them against human scores.
   * - 2
     - Lecture 6
     - **Settings, models and cost.** ``defaultTemperature``, ``defaultMaxTokens``, ``provider`` and
       ``defaultModel``. Comparing providers fairly. Reading Smarter's token and cost records, and
       the dashboard's cost charts.
   * - 2
     - Live session 2
     - Review of Assignment 1. Live comparison of three models on a shared test set, scored by the
       class. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Knowledge.** Why models make things up. Grounding with
       :doc:`Static </smarter-resources/plugin/plugin/static>` and
       :doc:`Skill </smarter-resources/plugin/plugin/skill>` plugins.
   * - 3
     - Lecture 8
     - **Retrieval.** Embeddings and similarity search, explained without mathematics. Loading
       documents into a :doc:`Vectorstore </smarter-resources/smarter-vectorstore>` and answering
       with citations.
   * - 3
     - Lecture 9
     - **Tools.** :doc:`Websearch </smarter-resources/plugin/plugin/websearch>` and :doc:`API
       </smarter-resources/plugin/plugin/api>` plugins. Smarter offers a plugin only when the prompt
       matches one of its ``searchTerms`` (exactly, with a typo, or as a synonym), and the model
       then decides, from the plugin's description, whether to call it. Reading plugin selection and
       tool calls in the Console.
   * - 3
     - Live session 3
     - Review of Assignment 2. Students debug tool calls that do not happen, using the Console.
       Capstone proposals are discussed in small groups. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Safety.** Prompt injection, jailbreaks and data leakage, shown live.
       :doc:`Guardrails </smarter-resources/smarter-guardrail>` and why they are enforced while a
       system prompt is only a request.
   * - 4
     - Lecture 11
     - **Workflows.** Breaking a job into steps with an
       :doc:`Orchestrator </smarter-resources/smarter-orchestrator>`, and when one prompt is
       better than several.
   * - 4
     - Lecture 12
     - **Designing for a real audience.** Interviewing a client, writing a welcome message and
       examples, branding with :doc:`styles </smarter-resources/llmclient/styles>`, and deploying.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4, three days before Live session 4. The capstone proposal (one paragraph) is due before Live
session 3, and the capstone at the start of Live session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: A Focused Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students turn the ``simple`` LLMClient into an assistant with one narrow job, using at least two of
the techniques from Lecture 3, and explain each design choice.

**Turn in:** the manifest in a GitHub repository, three example conversations, and a half-page
design note.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Manifest
     - 4
     - Valid, applies cleanly, and its welcome message and examples suit the job.
     - Applies only with help, or keeps defaults.
   * - System prompt
     - 6
     - Clear persona, audience, job, constraints and refusals.
     - The job or refusals are vague.
   * - Techniques
     - 6
     - Two techniques used where they help, visible in the conversations.
     - Techniques named but not used, or used where they do not help.
   * - Design note
     - 4
     - Explains why, not only what.
     - Restates the system prompt.

Assignment 2: An Evaluation Harness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a test set of twenty prompts and a five-criterion scoring rubric, score the answers
by hand, then build a judge LLMClient that scores them with the same rubric, and compare the
judge's scores with their own.

**Turn in:** the test set, the rubric, a spreadsheet of human and judge scores, the judge's
manifest, and a one-page analysis of where the judge agrees and disagrees.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Test set
     - 5
     - Varied: typical, edge, ambiguous and adversarial prompts.
     - Variations of one easy question.
   * - Rubric
     - 5
     - Observable criteria that two people would apply the same way.
     - Vague criteria such as "helpful".
   * - Judge
     - 5
     - Returns scores in a consistent format, using the rubric.
     - Returns free text, or ignores the rubric.
   * - Agreement analysis
     - 5
     - Quantifies agreement, and explains the disagreements.
     - Says only that the judge "mostly agrees".

Assignment 3: Grounded Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students give their assistant knowledge with a Vectorstore built from at least five real documents
(for example a course handbook, a club's rules or a product manual) and one tool plugin, then
measure with their evaluation harness whether answers improved.

**Turn in:** the manifests, the documents or links to them, before-and-after scores, and
Console screenshots of a retrieval and a tool call.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Retrieval
     - 6
     - Answers cite the right documents, and the assistant says when it does not know.
     - Retrieval works, but answers ignore it or invent sources.
   * - Tool plugin
     - 4
     - Called when it should be, and its result is used.
     - Never called, without explanation.
   * - Measured improvement
     - 6
     - Same test set and rubric before and after, with the change reported honestly.
     - No before-and-after comparison.
   * - Explanation
     - 4
     - Explains which questions improved and which did not, and why.
     - Reports scores without interpretation.

Assignment 4: Red Team Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students attack a classmate's assistant (assigned by the instructor) with at least ten attempts at
prompt injection, jailbreaking, going off topic or extracting its instructions, then write up the
results for the owner, who adds guardrails in response.

**Turn in:** an attack log from the journal, a two-page report with findings ranked by severity,
and, as the owner, the guardrail manifests that answer the report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Attack variety
     - 5
     - Ten or more attempts, across several techniques.
     - Repeats of the same attack.
   * - Report quality
     - 5
     - Each finding has the prompt, the result, a severity and a suggested fix.
     - Findings without evidence or fixes.
   * - Response as owner
     - 6
     - Guardrails stop the reported attacks without blocking normal use, with evidence.
     - Guardrails added but not tested, or block normal prompts.
   * - Professionalism
     - 4
     - Constructive and specific, as a security report should be.
     - Mocking or vague.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Deployed Assistant for a Real Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Take an AI assistant from a client's needs to a deployed, evaluated and
governed application, and hand it over.

Students interview a real client, build an LLMClient with retrieval, at least one tool plugin,
guardrails and custom styles, evaluate it with their harness, and have the instructor deploy it
so that the client can try it.

**What students turn in:**

- A Git repository with every manifest, the documents used for retrieval (or links), and a
  ``README.md`` that explains how to apply and maintain the assistant.
- A three-page design brief: the client, the audience, the job, the risks, and the reason for each
  plugin, guardrail and setting.
- The evaluation: test set of at least thirty prompts, rubric, scores and an analysis.
- Written feedback from the client, of a paragraph or more.
- A six-minute presentation with a live demonstration.

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
     - Design follows from the interview, and the client's feedback is addressed.
     - Generic assistant with a client's name.
   * - Prompt and grounding
     - 20
     - Answers are accurate, cited and on topic, and say when they do not know.
     - Accurate on easy questions, invents answers on hard ones.
   * - Governance
     - 15
     - Guardrails and a budget match the risks named in the brief.
     - Guardrails unrelated to the stated risks.
   * - Evaluation
     - 25
     - Thirty or more varied prompts, a clear rubric, and honest results that drove changes.
     - Few tests, or results that did not influence the design.
   * - Handover and presentation
     - 20
     - ``README.md`` lets someone else maintain it. Presentation is clear and on time.
     - No maintenance notes, or the presentation overruns.

Capstone B: Choosing a Model for an Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Run a rigorous, reproducible evaluation that answers a real business
question about models and prompts, and communicate it to decision makers.

A fictional organization (or a real one, with permission) wants one assistant for a defined job,
such as answering HR policy questions or drafting first replies to customer email. Students build
the same assistant on at least three models from at least two providers, each with its best
system prompt, and evaluate them on quality, latency, cost and safety.

**What students turn in:**

- A Git repository with every manifest, the test set of at least forty prompts, the rubric and the
  raw scores.
- A judge LLMClient, validated against human scores on at least ten answers.
- A four-page recommendation memo, with charts, for a non-technical manager: which model, which
  prompt, the expected monthly cost for a stated number of users, and the risks.
- A six-minute presentation of the recommendation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Evaluation design
     - 25
     - Fair comparison: each model's prompt tuned with the same effort, and the same tests.
     - One prompt tuned for one model and reused for the others.
   * - Validated judge
     - 15
     - Agreement with human scores measured and reported.
     - Judge used without checking.
   * - Cost and latency
     - 20
     - Measured from Smarter's records and projected to a monthly figure, with assumptions stated.
     - Taken from price lists, not measured.
   * - Safety
     - 15
     - Adversarial prompts included, and each model's failures reported.
     - Safety not tested.
   * - Memo and presentation
     - 25
     - A clear recommendation that a manager could act on, with the trade-offs stated.
     - Data without a recommendation.

Recommended Texts
-----------------

- **Required:** John Berryman and Albert Ziegler, *Prompt Engineering for LLMs* (O'Reilly, 2024).
  Week 1: chapters 1 to 4. Week 2: chapters 5, 6 and 10. Week 3: chapters 7 to 9. Week 4:
  chapter 11.
- **Required:** Chip Huyen, *AI Engineering: Building Applications with Foundation Models*
  (O'Reilly, 2025). Week 2: chapters 3 and 4, on evaluation. Week 3: chapter 6, on retrieval and
  agents.
- **Background:** Ethan Mollick, *Co-Intelligence: Living and Working with AI* (Portfolio, 2024).
- **Smarter documentation:** :doc:`/smarter-resources/smarter-llmclient`,
  :doc:`/smarter-resources/smarter-plugin`, :doc:`/smarter-resources/smarter-vectorstore`,
  :doc:`/smarter-resources/smarter-guardrail`, :doc:`/smarter-resources/smarter-orchestrator` and
  :doc:`/smarter-platform/cost-accounting`.

Further Study
-------------

.. include:: further-study.txt
