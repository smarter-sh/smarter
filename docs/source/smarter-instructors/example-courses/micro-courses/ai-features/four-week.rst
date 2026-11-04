AI Features in Software: Four-Week Online Course
================================================

A four-week online course on putting LLMs inside a piece of software, safely, taught on the Doodle
of Smarter's web console: the sign-in page's illustration, which a Smarter LLMClient, the `Doodle
Editor
<https://github.com/smarter-sh/example-manifests/blob/main/smarter/llm-clients/llmclient-smarter-doodle-editor.yaml>`__,
chooses each day, and another, the `Doodle Artist
<https://github.com/smarter-sh/example-manifests/blob/main/smarter/llm-clients/llmclient-smarter-doodle-artist.yaml>`__,
draws. The whole feature is open source, in `apps/doodle/
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/doodle>`__, with its history
in three commits that grow it from a calendar. There are twelve 30-minute recorded lectures and a
90-minute live session each week. Week 1 covers the feature and its AI parts, week 2 prompting
from code and the contract with the model, week 3 judges, sanitizers and tests, and week 4
people, operations and shipping. See :doc:`../course-formats` for the format, the grading scale
and the course policies, and :doc:`../ai-features` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Python developers who want to add LLM features to software they build.
   * - **Deployment**
     - Each student runs Smarter from source (``make init``), with the example manifests loaded
       and a superuser login. Students change code and approve doodles in the Django admin, so a
       shared instance doesn't suit this course. Week 1 includes time for setup.
   * - **Models**
     - The models that the Doodle's manifests name, through the instructor's OpenAI key, and
       OpenAI's moderation model.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Under $10 per student in model charges, capped with a
       :doc:`Budget </smarter-resources/smarter-budget>`. Assignment 4 and Capstone B prompt the
       most.

Learning Objectives
-------------------

By the end of the course, students can:

1. Decide which parts of a feature a model should do and which code should do, and build the
   feature's safe answer first.
2. Declare a feature's AI parts as Smarter LLMClients and Guardrails, and prompt them from Python.
3. Design a model's request and answer as a validated contract with a menu of choices, and check
   every answer, and every input to the prompt, in code.
4. Evaluate a judge model's accuracy on labeled examples, and decide whether a feature fails open
   or closed.
5. Defend a feature against generated markup and a model's mistakes with an allowlist sanitizer
   and tests in which the model is patched.
6. Design the human review, audit trail, switches, disclosure and cost controls that a feature
   needs before its AI output reaches users.

Technical Prerequisites
-----------------------

- **Required:** Python: functions, classes, exceptions and type hints, and JSON.
- **Required:** Git, GitHub and pull requests, with a fork of `smarter
  <https://github.com/smarter-sh/smarter>`__.
- **Required by the end of week 1:** Docker, and Smarter installed from source with a superuser
  login, showing the sign-in page's doodle. See the :doc:`Smarter Instructor Guide
  </smarter-instructor>`.
- **Helpful:** `Pydantic <https://docs.pydantic.dev/>`__ models, Python's ``unittest.mock``,
  reading a Django app, `YAML <https://learnxinyminutes.com/docs/yaml/>`__, and having called an
  LLM API.
- **Not needed:** JavaScript or React, machine learning, or SVG. The course reads the Doodle's
  React app and SVG, but students don't write either.

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
     - **The newsroom.** A feature as desks: the calendar, the editor, the platform's checks, the
       tone judge, the artist, the sanitizer and a superuser. Which jobs suit a model (taste,
       judgment, drawing), which suit code (rules, limits, security), and which need a person.
       The `blog post <https://blog.smarter.sh/2026/11/04/smarter-doodle-llm-editor-artist/>`__.
   * - 1
     - Lecture 2
     - **The safe answer first.** Phase 1 (`commit 0df9280ff
       <https://github.com/smarter-sh/smarter/commit/0df9280ff18c1155b6d1b8111a35dd42ec6d3302>`__):
       the catalog and its schedules, regions from a time zone and nothing else, the planner,
       the models and the switches. What visitors see when every AI part fails.
   * - 1
     - Lecture 3
     - **AI resources as configuration.** The editor's and artist's manifests: model,
       temperature, system prompt, example prompts, ``staffOnly`` and output Guardrails. Why a
       prompt belongs in YAML, not in code: who changes it, how, and what comes with it.
       :doc:`/smarter-resources/smarter-llmclient`.
   * - 1
     - Live session 1
     - Setup triage. The editor in the workbench, live, with its example prompts and a request
       the class writes together. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Prompting from code.** ``prompting.py``: ``single_use_api_key()``, ``prompt_llmclient()``
       and ``assistant_text()``. Why the platform prompts its own chat api rather than a
       provider's SDK: the journal, cost accounting and Guardrails. Extracted from
       ``verify_stackademy``, not copied (:doc:`ADR 033 </adr/033-dry>`); phase 2 (`commit
       d07b91f67
       <https://github.com/smarter-sh/smarter/commit/d07b91f677ff0b8428ac36c62be9b5670f7492b1>`__).
   * - 2
     - Lecture 5
     - **A menu, not a blank page.** ``editor_request()`` and the Pydantic contract,
       ``DoodleEditorRequest`` and ``DoodleEditorDecision`` (:doc:`ADR 031
       </adr/031-pydantic-over-json>`). Always offering ``default``, and asking for a ``reason``.
       ``parse_answer()`` and what happens to an answer that doesn't validate.
   * - 2
     - Lecture 6
     - **Checks in code, on the way out and the way in.** ``check_decision()`` enforcing what the
       prompt asks; ``has_blocked_word()`` and the language matching in ``nlp.py``, and why an
       allowlist beats a blocklist for news. Phase 3's trends (`commit 2e6cb0806
       <https://github.com/smarter-sh/smarter/commit/2e6cb0806c126bcdf064f278d785f2901665aaa8>`__):
       ``region_trends()``, ``is_a_person()`` and ``is_an_occasion()``, fetched with
       ``safe_http.py`` and cached.
   * - 2
     - Live session 2
     - Review of Assignment 1. Writing a management command that prompts the editor, together,
       and reading its prompt in the journal. Start Assignment 2.
   * - 3
     - Lecture 7
     - **A second model as judge.** The ``llm_judge`` strategy and ``upbeat_occasion_input``.
       ``tone_check()`` fails closed, and declined a Diwali trend; why that trade is right here
       and wrong elsewhere. Model quirks and the judge's retry in ``model_quirks.py``.
       :doc:`/smarter-resources/smarter-guardrail`.
   * - 3
     - Lecture 8
     - **Generated markup is untrusted.** What an SVG can carry. ``sanitize.py``: allowlisted
       elements and attributes, CSS limited to the drawing's own classes, size caps.
       ``compose_svg()`` in ``artwork.py``, ``<img>``, and the artwork's Content-Security-Policy.
       The chat widget's same problem, in `DOMPurify and Markdown
       <https://blog.smarter.sh/2026/08/03/smarter-chat-untrusted-html/>`__.
   * - 3
     - Lecture 9
     - **Testing a feature whose model is patched out.** ``test_editor.py``: a test for every
       refusal and failure. Saved drawings in ``tests/data/artist/`` and saved Wikimedia
       responses, so no test needs the network or a model. Running the app's tests in the
       container.
   * - 3
     - Live session 3
     - Review of Assignment 2. A red-team workshop: the class attacks the editor and the artist,
       and traces each attempt to the layer that stopped it. Capstone proposals discussed. Start
       Assignment 3.
   * - 4
     - Lecture 10
     - **People and paper trails.** Proposed drawings, *Preview the week*, Approve and Reject in
       ``admin.py``; ``DoodleEditorRun``; a person's choice never replanned;
       ``enable_doodle_auto_approve`` off by default; and the credit line that tells visitors an
       AI chose or drew the doodle (`commit f00ac5cac
       <https://github.com/smarter-sh/smarter/commit/f00ac5cac5fb7d16859c239a9cbae491c428c6c7>`__).
   * - 4
     - Lecture 11
     - **Running it.** Celery Beat every six hours, ``EDITOR_MAX_ATTEMPTS``, a day asked once;
       caching fallbacks that keep the page whole while a drawing awaits approval; the api
       contract and the React app; and a platform without the manifests, where the calendar does
       the whole job.
   * - 4
     - Lecture 12
     - **Cost and design review.** Reading a feature's cost per day from the journal, capping it
       with a Budget, and choosing cheaper models for judges. The blog post's takeaways as a
       checklist for reviewing any AI feature, applied to a feature the students use every day.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: The Editor's Taste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students apply a copy of the Doodle Editor's manifest with an editorial policy of their own, such
as science and education only, and run the same five requests through both editors, including two
that tempt the model off the menu. They compare the choices and reasons, and say which of them
``check_decision()`` would refuse.

**Turn in:** the manifest, and a three-page Markdown report with each request, both answers and
the analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - A working manifest
     - 4
     - Applies cleanly; the policy is stated in the system prompt, not scattered.
     - Edits that contradict the rest of the prompt.
   * - Evidence
     - 6
     - Real answers from both editors, pasted as they came.
     - Paraphrased, or one editor only.
   * - Analysis
     - 6
     - Explains each difference by a line of the prompts, and reads the reasons.
     - Lists differences without explaining them.
   * - The off-menu attempts
     - 4
     - Shows what the model did, and names the check that would catch it.
     - Assumes the prompt is enough.

Assignment 2: Prompting From Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a management command in their fork that prompts their copy of the editor for a
day, with ``editor_request()`` and the helpers in ``prompting.py``, and prints each decision with
the verdict of ``check_decision()``. The api key it uses must be deleted even when the prompt
fails, and the command must be tested with the model patched.

**Turn in:** a pull request against their own fork, the command's output for two days, and its
test output from the container.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Uses the platform
     - 5
     - Prompts through ``prompting.py``; the prompt shows in the journal.
     - Calls a provider's SDK directly.
   * - Parses and checks
     - 5
     - ``parse_answer()`` and ``check_decision()`` on every decision, refusals printed with why.
     - Prints the raw answer.
   * - Cleans up
     - 4
     - The api key is deleted on success and failure, and a test proves it.
     - A key left behind when the prompt fails.
   * - Tested
     - 6
     - Tests with the model patched, in the style of ``test_commands.py``.
     - Untested, or tested by prompting a model.

Assignment 3: Trust Nothing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write at least eight tests that feed crafted answers through ``parse_answer()`` and
``check_decision()``, and crafted trends through ``region_trends()``, with the model and the
network patched. They look for one input that passes but shouldn't, and propose a fix.

**Turn in:** a pull request against their own fork with the tests, their output from the
container, and a paragraph on the gap they found, or why they found none.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Cases covered
     - 7
     - Answers and trends, eight or more distinct ways to fail, each asserting the reason given.
     - Only malformed JSON and off-menu.
   * - Isolation
     - 4
     - No real prompts or requests; saved responses, as in ``test_trends.py``.
     - Tests that call the LLM or Wikipedia.
   * - The gap
     - 6
     - A real gap with a failing test and a fix, or a convincing search that found none.
     - "The checks look fine."
   * - Runs as shown
     - 3
     - Output from the container matches the pull request.
     - Took the tests' passing on trust; output not included.

Assignment 4: A Judge, Measured
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write an ``llm_judge`` Guardrail for a criterion that code can't check, label twenty
inputs by hand, and run each through the Guardrail with ``evaluate()``, as ``tone_check()``
does. They report its false positives and false negatives, try one change to its prompt or
threshold, and say whether a feature that uses it should fail open or closed.

**Turn in:** the Guardrail's manifest, the labeled inputs and results as a table, and a one-page
analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - A fair test set
     - 5
     - Labeled before running, with hard cases on both sides of the line.
     - Twenty easy cases, or labels chosen after the results.
   * - Results
     - 5
     - Every input's verdict and score, recorded as they came.
     - A summary without the data.
   * - The change
     - 4
     - One change, measured on the same set, kept or reverted on the evidence.
     - Several changes at once, or none measured.
   * - Fail open or closed
     - 6
     - A decision argued from what each kind of error costs the feature.
     - "Closed, to be safe," with no costs weighed.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: An AI Feature of Your Own
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an AI feature into software, with its AI parts as Smarter resources,
its safety in code, and a person in the loop.

In their fork of Smarter, or in a Django project of their own that prompts a Smarter platform,
students build a feature in which an LLMClient makes a choice or writes something that users see:
a tip of the day picked from the documentation, a suggested description for a new resource, or a
summary of an account's week. It must work without the model, give the model a menu or a schema,
check every answer in code, judge what code can't check with a Guardrail, record what was asked
and answered, let a person approve or override what is new, have a switch, and say on the page
when an AI made it. A feature meant for Smarter itself must be agreed with the maintainers in a
GitHub issue first.

**What students turn in:**

- A pull request against their own fork, with the LLMClient's and Guardrail's manifests.
- Tests with the model patched, and their output, with at least 90% coverage of the feature's
  code.
- A two-page design note: the feature's desks, what each check guards against, whether each one
  fails open or closed and why, and the cost per day from the journal.
- A six-minute presentation, including one answer the code refuses and one a person rejects.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - A safe answer first
     - 15
     - The feature works, and says nothing wrong, with the model off.
     - Breaks or shows an error without the model.
   * - Contract and checks
     - 20
     - A validated request and answer, and every rule of the prompt enforced in code.
     - Trusts the prompt.
   * - Judge and review
     - 20
     - A judge for what code can't check, and a person approves what is new.
     - The model's output goes straight to users.
   * - Record, control, disclosure
     - 15
     - What was asked and answered is kept; a switch turns the AI off; the page credits it.
     - No record, no switch, or no disclosure.
   * - Tests
     - 20
     - Refusals and failures tested, with the model patched, at 90% coverage or more.
     - Only the happy path, or tests that prompt a model.
   * - Design note
     - 10
     - Each check tied to the failure it prevents and its cost.
     - A description of the code.

Capstone B: Red Team the Newsroom
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Evaluate an AI feature's defenses with evidence, layer by layer, and
strengthen the weakest.

On their own platform, students attack the Doodle with at least forty cases: requests that tempt
the editor off the menu, trend titles written to inject instructions, occasions that are sad but
contain no blocked word, and briefs that ask the artist for scripts, links, external images or a
drawing over the base scene. For each case they record which layer stopped it: the prompt, an
output Guardrail, ``check_decision()``, the trends filter, the judge, the sanitizer, or the person
in the admin. They fix the two weakest points they find, each with a test that fails before the
fix.

**What students turn in:**

- A table of the cases, with the input, what each model answered, and the layer that stopped it,
  or none.
- A four-page analysis of where the defenses overlap and where they are thin, citing the code
  and the commits.
- A pull request against their own fork with the two fixes and their tests.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Range of attacks
     - 20
     - Every layer is tested, with cases a careful attacker would try.
     - Forty variants of one attack.
   * - Evidence
     - 20
     - Real answers and editor runs, recorded as they came.
     - Results from memory, or assumed from the code.
   * - Attribution to layers
     - 20
     - Each case traced to the code or resource that stopped it.
     - "It was blocked."
   * - The fixes
     - 25
     - Failing tests, then fixes that pass without breaking the app's other tests.
     - Suggestions without tests.
   * - Writing
     - 15
     - Concise, organized and specific.
     - Long or general.

Recommended Texts
-----------------

- **Required:** `How Two Smarter LLMClients Create the Sign-in Page's Daily Doodle
  <https://blog.smarter.sh/2026/11/04/smarter-doodle-llm-editor-artist/>`__ and
  :doc:`/smarter-framework/developer-reference/react-integration/doodle`, in week 1.
- **Required:** :doc:`/smarter-resources/smarter-llmclient`, in week 1.
- **Required:** :doc:`/smarter-resources/smarter-guardrail` and `LLM Guardrails in YAML: How
  Smarter Declares, Orders and Audits Them
  <https://blog.smarter.sh/2026/06/11/smarter-llm-guardrails-yaml/>`__, in week 3.
- **Required:** the `OWASP Top 10 for LLM Applications <https://genai.owasp.org/llm-top-10/>`__,
  on prompt injection and improper output handling, in week 3.
- **Reference:** Chip Huyen, *AI Engineering* (O'Reilly, 2025), on evaluation, guardrails and the
  architecture of AI applications.
- **Reference:** John Berryman and Albert Ziegler, *Prompt Engineering for LLMs* (O'Reilly, 2024),
  on designing the prompts and answers that software consumes.
- **In the repository:** `editor.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/editor.py>`__,
  `prompting.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/prompting.py>`__,
  `sanitize.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/sanitize.py>`__
  and the three Doodle commits, in order.

Further Study
-------------

.. include:: further-study.txt
